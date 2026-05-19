"""Reciprocal rank fusion for dense + BM25 candidate lists."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Sequence, Tuple


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[Tuple[str, float]]],
    *,
    rrf_k: int = 60,
    top_n: int = 50,
) -> List[Tuple[str, float]]:
    """Fuse ranked lists of (chunk_id, score) into a single ranking."""
    fused: Dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, (chunk_id, _score) in enumerate(ranking, start=1):
            fused[chunk_id] += 1.0 / (rrf_k + rank)
    ordered = sorted(fused.items(), key=lambda item: item[1], reverse=True)
    return ordered[:top_n]
