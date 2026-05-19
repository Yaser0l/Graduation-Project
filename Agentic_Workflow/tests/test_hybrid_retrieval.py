"""Unit tests for BM25 + RRF hybrid retrieval helpers."""
from __future__ import annotations

from src.rag.bm25_index import BM25Index, tokenize
from src.rag.hybrid import reciprocal_rank_fusion


class TestHybridRetrieval:
    def test_tokenize_codes(self):
        assert "p0420" in tokenize("OBD-II code P0420 catalyst")

    def test_bm25_prefers_exact_code(self):
        texts = [
            "P0420 Catalyst System Efficiency Below Threshold",
            "Unrelated tire pressure maintenance text",
        ]
        metas = [{"type": "dtc", "code": "P0420"}, {"type": "manual"}]
        ids = ["dtc:generic:P0420", "manual:1"]
        index = BM25Index.build(texts, metas, ids)
        hits = index.search("P0420 catalyst efficiency", k=2)
        assert hits[0][0] == "dtc:generic:P0420"

    def test_rrf_fuses_two_lists(self):
        dense = [("a", 0.9), ("b", 0.8)]
        bm25 = [("b", 3.0), ("c", 2.0)]
        fused = reciprocal_rank_fusion([dense, bm25], top_n=3)
        ids = [cid for cid, _ in fused]
        assert "b" in ids
        assert len(ids) == 3
