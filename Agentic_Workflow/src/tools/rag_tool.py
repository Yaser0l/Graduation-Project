"""RAG retrieval tool."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from langchain_core.documents import Document
from langchain_core.tools import tool

import config
from src.rag.retrieval_trace import format_trace

logger = logging.getLogger(__name__)

_CODE_RE = re.compile(r"\b[PCBU][0-9]{4}\b", re.IGNORECASE)


def _kb():
    from src.rag.knowledge_base import knowledge_base

    return knowledge_base


def _log_retrieval_trace(trace) -> None:
    text = format_trace(trace, max_content=500)
    logger.info("RAG retrieval trace:\n%s", text)
    print("\n" + "=" * 60)
    print("RAG RETRIEVAL TRACE")
    print("=" * 60)
    print(text)
    print("=" * 60 + "\n")


@tool
def retrieve_automotive_knowledge(query: str, top_k: int = 5) -> str:
    """Retrieve relevant automotive repair information from the knowledge base."""
    pairs, trace = _kb().retrieve_detailed(query, k=top_k)
    _log_retrieval_trace(trace)
    if not pairs:
        return "No relevant information found in the knowledge base."
    results = []
    for i, (doc, score) in enumerate(pairs, 1):
        meta = doc.metadata or {}
        results.append(
            f"[Result {i}] cosine/final={score:.4f}\n"
            f"{doc.page_content}\n"
            f"Metadata: {meta}\n"
        )
    return "\n".join(results)


@tool
def retrieve_with_reflection(query: str, top_k: int = 5) -> Dict[str, Any]:
    """Retrieve automotive information with quality reflection and full score trace."""
    kb = _kb()
    pairs, trace = kb.retrieve_detailed(query, k=top_k)

    # If query names a DTC, prepend exact metadata hit
    code_match = _CODE_RE.search(query or "")
    if code_match:
        exact = kb.lookup_dtc_code(code_match.group(0).upper())
        if exact:
            meta = exact.metadata or {}
            trace.notes.append(f"prepended exact DTC hit for {meta.get('code')}")
            if not any(h.chunk_id == meta.get("chunk_id") for h in trace.hits):
                from src.rag.retrieval_trace import ScoredHit

                trace.hits.insert(
                    0,
                    ScoredHit(
                        rank=0,
                        chunk_id=meta.get("chunk_id", ""),
                        content=exact.page_content,
                        metadata=dict(meta),
                        cosine_similarity=1.0,
                        final_score=1.0,
                        source="exact_dtc",
                    ),
                )
                pairs = [(exact, 1.0)] + [
                    (d, s) for d, s in pairs if (d.metadata or {}).get("chunk_id") != meta.get("chunk_id")
                ][: top_k - 1]

    _log_retrieval_trace(trace)

    if not pairs:
        return {
            "content": "No relevant information found.",
            "is_sufficient": False,
            "score": 0.0,
            "reflection": "No documents retrieved. Consider web search.",
            "document_count": 0,
            "retrieval_trace": trace.to_dict(),
            "hits": [],
        }

    docs = [doc for doc, _ in pairs]
    is_sufficient, avg_score, reflection = kb.reflect_on_retrieval(query, docs)

    content_parts = []
    for i, hit in enumerate(trace.hits, 1):
        cos = hit.cosine_similarity
        cos_s = f"{cos:.4f}" if cos is not None else "n/a"
        content_parts.append(
            f"[Source {i}] score={hit.final_score:.4f} cosine={cos_s} "
            f"chunk_id={hit.chunk_id}\n{hit.content}"
        )
    content = "\n\n".join(content_parts)

    return {
        "content": content,
        "is_sufficient": is_sufficient,
        "score": avg_score,
        "reflection": reflection,
        "document_count": len(pairs),
        "retrieval_trace": trace.to_dict(),
        "hits": [h.to_dict() for h in trace.hits],
    }


def retrieve_for_codes(
    codes: List[str],
    make: str = None,
    filter_by_type: bool = True,
) -> str:
    """Retrieve information for multiple OBD2 codes (exact lookup first, then semantic)."""
    kb = _kb()
    results: List[str] = []

    for code in codes:
        code = code.upper().strip()
        results.append(f"=== Information for {code} ===")

        if filter_by_type:
            exact = kb.lookup_dtc_code(code, make=make)
            if exact:
                meta = exact.metadata or {}
                results.append(
                    f"[exact metadata match] make={meta.get('make')} "
                    f"cosine=1.0000 chunk_id={meta.get('chunk_id')}\n{exact.page_content}"
                )
                results.append("")
                continue

        query = f"OBD2 code {code} diagnostic trouble code meaning causes repair"
        filter_dict = {"type": "dtc"} if filter_by_type else None
        pairs, trace = kb.retrieve_detailed(query, k=10, filter_dict=filter_dict)

        code_matched = [
            (d, s) for d, s in pairs if (d.metadata.get("code") or "").upper() == code
        ]
        if code_matched:
            pairs = code_matched
        elif filter_by_type:
            trace.notes.append(f"no chunk with metadata.code=={code}; showing best semantic hits")

        if make and filter_by_type and pairs:
            make_lower = make.lower()
            preferred = [
                (d, s)
                for d, s in pairs
                if (d.metadata.get("make") or "").lower() in (make_lower, "generic")
            ]
            pairs = preferred[:3] if preferred else pairs[:3]
        else:
            pairs = pairs[:3]

        for doc, score in pairs:
            meta = doc.metadata or {}
            hit = next((h for h in trace.hits if h.chunk_id == meta.get("chunk_id")), None)
            cos = hit.cosine_similarity if hit else score
            cos_s = f"{cos:.4f}" if cos is not None else f"{score:.4f}"
            results.append(
                f"[semantic] cosine={cos_s} rerank={score:.4f} "
                f"make={meta.get('make')} chunk_id={meta.get('chunk_id')}\n{doc.page_content}"
            )
        results.append("")

    return "\n".join(results) if results else "No information found for the provided codes."
