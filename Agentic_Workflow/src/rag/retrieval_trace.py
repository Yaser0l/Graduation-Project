"""Structured retrieval audit trail (scores, vectors, metadata)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScoredHit:
    """One retrieved chunk with full scoring breakdown."""

    rank: int
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    dense_distance: Optional[float] = None
    cosine_similarity: Optional[float] = None
    bm25_score: Optional[float] = None
    rrf_score: Optional[float] = None
    rerank_score: Optional[float] = None
    final_score: float = 0.0
    source: str = "hybrid"  # exact_dtc | dense | bm25 | hybrid | rerank
    query_vector_preview: Optional[List[float]] = None
    doc_vector_preview: Optional[List[float]] = None
    embedding_dim: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalTrace:
    """Full retrieval run for logging / API responses."""

    query: str
    hits: List[ScoredHit] = field(default_factory=list)
    candidate_count: int = 0
    hybrid_enabled: bool = False
    rerank_enabled: bool = False
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "candidate_count": self.candidate_count,
            "hybrid_enabled": self.hybrid_enabled,
            "rerank_enabled": self.rerank_enabled,
            "notes": self.notes,
            "hits": [h.to_dict() for h in self.hits],
        }


def chroma_distance_to_cosine(distance: float) -> float:
    """Chroma cosine space: similarity = 1 - distance (vectors are L2-normalized)."""
    return max(0.0, min(1.0, 1.0 - float(distance)))


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def vector_preview(vec: List[float], dims: int = 8) -> List[float]:
    return [round(float(x), 6) for x in vec[:dims]]


def format_trace(trace: RetrievalTrace, *, max_content: int = 400) -> str:
    lines = [
        f"Query: {trace.query}",
        f"Candidates: {trace.candidate_count} | hybrid={trace.hybrid_enabled} | rerank={trace.rerank_enabled}",
    ]
    for note in trace.notes:
        lines.append(f"  note: {note}")
    for hit in trace.hits:
        lines.append("")
        lines.append(f"--- Rank {hit.rank} | {hit.source} | chunk_id={hit.chunk_id} ---")
        meta = hit.metadata or {}
        lines.append(
            f"  scores: cosine={hit.cosine_similarity} dense_dist={hit.dense_distance} "
            f"bm25={hit.bm25_score} rrf={hit.rrf_score} rerank={hit.rerank_score} final={hit.final_score:.4f}"
        )
        if hit.query_vector_preview is not None:
            lines.append(f"  query_vec[{hit.embedding_dim}] preview: {hit.query_vector_preview}")
        if hit.doc_vector_preview is not None:
            lines.append(f"  doc_vec[{hit.embedding_dim}] preview: {hit.doc_vector_preview}")
        lines.append(f"  meta: type={meta.get('type')} code={meta.get('code')} make={meta.get('make')} page={meta.get('page')}")
        preview = (hit.content or "")[:max_content]
        lines.append(f"  text: {preview}{'...' if len(hit.content or '') > max_content else ''}")
    return "\n".join(lines)
