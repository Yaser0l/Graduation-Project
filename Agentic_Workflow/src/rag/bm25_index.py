"""Persisted BM25 lexical index for hybrid retrieval."""
from __future__ import annotations

import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from langchain_core.documents import Document

_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _metadata_matches(meta: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
    for key, value in filter_dict.items():
        if meta.get(key) != value:
            return False
    return True


@dataclass
class BM25Index:
    """In-memory BM25 over indexed chunk texts."""

    corpus: List[str]
    metadatas: List[Dict[str, Any]]
    chunk_ids: List[str]
    _bm25: Any = None

    @classmethod
    def build(
        cls,
        texts: Sequence[str],
        metadatas: Sequence[Dict[str, Any]],
        chunk_ids: Sequence[str],
    ) -> "BM25Index":
        from rank_bm25 import BM25Okapi

        tokenized = [tokenize(t) for t in texts]
        index = cls(list(texts), list(metadatas), list(chunk_ids))
        index._bm25 = BM25Okapi(tokenized)
        return index

    def search(
        self,
        query: str,
        k: int = 50,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float]]:
        """Return (chunk_id, bm25_score) pairs, highest first."""
        if not self.corpus or self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        query_tokens = set(tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
        out: List[Tuple[str, float]] = []
        for idx, score in ranked:
            meta = self.metadatas[idx]
            if filter_dict and not _metadata_matches(meta, filter_dict):
                continue
            effective = float(score)
            if effective <= 0.0 and query_tokens:
                overlap = query_tokens & set(tokenize(self.corpus[idx]))
                if not overlap:
                    continue
                effective = len(overlap) * 0.01
            out.append((self.chunk_ids[idx], effective))
            if len(out) >= k:
                break
        return out

    def document_for_chunk_id(self, chunk_id: str) -> Optional[Document]:
        try:
            idx = self.chunk_ids.index(chunk_id)
        except ValueError:
            return None
        return Document(page_content=self.corpus[idx], metadata=dict(self.metadatas[idx]))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "corpus": self.corpus,
            "metadatas": self.metadatas,
            "chunk_ids": self.chunk_ids,
        }
        path.write_bytes(pickle.dumps(payload))

    @classmethod
    def load(cls, path: Path) -> "BM25Index":
        payload = pickle.loads(path.read_bytes())
        texts = payload["corpus"]
        metas = payload["metadatas"]
        chunk_ids = payload["chunk_ids"]
        return cls.build(texts, metas, chunk_ids)
