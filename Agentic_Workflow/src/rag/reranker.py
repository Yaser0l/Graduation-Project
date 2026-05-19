"""Cross-encoder reranking (production-aligned with BGE reranker family)."""
from __future__ import annotations

import logging
import threading
from typing import List, Optional, Tuple

from langchain_core.documents import Document

from src.rag.bge_m3_embeddings import resolve_torch_device

logger = logging.getLogger(__name__)

_reranker_lock = threading.Lock()
_reranker_instance: Optional["BGEReranker"] = None


class BGEReranker:
    """Lazy-loaded sentence-transformers CrossEncoder."""

    def __init__(self, model_name: str, device: str | None = None) -> None:
        from sentence_transformers import CrossEncoder

        torch_device = resolve_torch_device(device)
        logger.info("Loading reranker %s on %s", model_name, torch_device)
        self.model_name = model_name
        self._model = CrossEncoder(model_name, device=torch_device)

    def rerank(
        self,
        query: str,
        documents: List[Document],
        *,
        top_n: int = 5,
    ) -> List[Tuple[Document, float]]:
        if not documents:
            return []
        pairs = [[query, doc.page_content or ""] for doc in documents]
        scores = self._model.predict(pairs, show_progress_bar=len(pairs) > 32)
        ranked = sorted(zip(documents, scores), key=lambda item: float(item[1]), reverse=True)
        return [(doc, float(score)) for doc, score in ranked[:top_n]]


def get_reranker(model_name: str, device: str | None = None) -> BGEReranker:
    global _reranker_instance
    if _reranker_instance is None:
        with _reranker_lock:
            if _reranker_instance is None:
                _reranker_instance = BGEReranker(model_name, device=device)
    return _reranker_instance
