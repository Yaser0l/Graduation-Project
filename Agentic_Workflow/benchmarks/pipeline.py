"""Production-equivalent RAG pipeline used for benchmarking.

Re-uses the same Chroma + HuggingFaceEmbeddings knowledge base instance the
agents talk to in production, then asks the configured LLM (default GLM-5.1)
to answer the question grounded in the retrieved chunks. The pipeline only
exposes the bits RAGAS needs (`response`, `retrieved_contexts`) so we can swap
implementations later without touching the eval code.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .settings import BenchmarkSettings


def _knowledge_base():
    """Lazy import so importing this module doesn't force Chroma + ST init."""
    from src.rag.knowledge_base import knowledge_base  # noqa: WPS433
    return knowledge_base

logger = logging.getLogger(__name__)

_GROUNDED_SYSTEM_PROMPT = (
    "You are an expert automotive diagnostic assistant. Answer the user's "
    "question using ONLY the provided reference context. If the context does "
    "not contain the answer, reply exactly: 'I do not have enough information.' "
    "Do not invent facts and do not reference sources the user cannot see."
)

_USER_TEMPLATE = (
    "Reference context:\n{context}\n\n"
    "Question: {question}\n\n"
    "Provide a concise, technically accurate answer."
)


@dataclass
class RagAnswer:
    """Result of a single pipeline invocation."""

    question: str
    response: str
    retrieved_contexts: List[str]
    retrieval_scores: List[float]


class RagPipeline:
    """Thread-safe wrapper around the production retrieve-and-generate flow."""

    def __init__(self, settings: BenchmarkSettings):
        self.settings = settings
        self._llm: Optional[ChatOpenAI] = None
        self._llm_lock = threading.Lock()

    # --- internals --------------------------------------------------------

    def _build_llm(self) -> ChatOpenAI:
        kwargs = {
            "model": self.settings.judge_model,
            "temperature": self.settings.judge_temperature,
            "timeout": self.settings.request_timeout_sec,
            "max_retries": self.settings.max_retries,
            "api_key": self.settings.api_key,
        }
        if self.settings.base_url:
            kwargs["base_url"] = self.settings.base_url
        return ChatOpenAI(**kwargs)

    def _llm_singleton(self) -> ChatOpenAI:
        if self._llm is None:
            with self._llm_lock:
                if self._llm is None:
                    self._llm = self._build_llm()
        return self._llm

    @staticmethod
    def _format_context(contexts: List[str]) -> str:
        if not contexts:
            return "(no reference context retrieved)"
        return "\n\n".join(f"[Source {i + 1}] {c}" for i, c in enumerate(contexts))

    # --- public API -------------------------------------------------------

    def retrieve(self, question: str) -> RagAnswer:
        """Run retrieval only — useful for offline retrieval-quality metrics."""
        docs_with_scores = _knowledge_base().retrieve_with_scores(question, k=self.settings.top_k)
        contexts = [doc.page_content for doc, _ in docs_with_scores]
        # Chroma returns distance; convert to a 0-1 similarity for stable sort.
        scores = [1.0 / (1.0 + float(score)) for _, score in docs_with_scores]
        return RagAnswer(question=question, response="", retrieved_contexts=contexts, retrieval_scores=scores)

    def answer(self, question: str) -> RagAnswer:
        """Retrieve, then generate a grounded answer with the configured LLM."""
        retrieved = self.retrieve(question)
        prompt = _USER_TEMPLATE.format(
            context=self._format_context(retrieved.retrieved_contexts),
            question=question,
        )
        llm = self._llm_singleton()
        try:
            result = llm.invoke([
                SystemMessage(content=_GROUNDED_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
            response = (result.content or "").strip()
        except Exception as exc:  # never let one case kill the whole run
            logger.warning("Pipeline LLM call failed for question=%r: %s", question, exc)
            response = ""

        return RagAnswer(
            question=question,
            response=response,
            retrieved_contexts=retrieved.retrieved_contexts,
            retrieval_scores=retrieved.retrieval_scores,
        )
