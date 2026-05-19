"""Deterministic embeddings for tests and CI (no sentence-transformers load)."""
from __future__ import annotations

from typing import List


class DeterministicEmbeddings:
    """Fixed-size vectors derived from text hash (tests only; no GPU)."""

    def __init__(self, dim: int = 384) -> None:
        self._dim = dim

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._vec(text)

    def _vec(self, text: str) -> List[float]:
        seed = sum(ord(c) for c in (text or "")) % 97
        return [0.01 * ((seed + i) % 17) for i in range(self._dim)]
