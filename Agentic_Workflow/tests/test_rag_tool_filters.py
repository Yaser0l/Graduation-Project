"""Tests for retrieve_for_codes metadata filters (SC-19)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from src.rag.retrieval_trace import RetrievalTrace
from src.tools import rag_tool
from src.tools.rag_tool import retrieve_for_codes


class TestRetrieveForCodesFilters:
    def test_uses_exact_lookup_before_semantic(self):
        mock_kb = MagicMock()
        exact = Document(
            page_content="C0561 exact",
            metadata={"type": "dtc", "code": "C0561", "make": "generic"},
        )
        mock_kb.lookup_dtc_code.return_value = exact
        with patch.object(rag_tool, "_kb", lambda: mock_kb):
            out = retrieve_for_codes(["C0561"], filter_by_type=True)
        mock_kb.lookup_dtc_code.assert_called_once_with("C0561", make=None)
        mock_kb.retrieve_detailed.assert_not_called()
        assert "exact metadata match" in out
        assert "C0561 exact" in out

    def test_semantic_fallback_when_no_exact(self):
        mock_kb = MagicMock()
        mock_kb.lookup_dtc_code.return_value = None
        doc = Document(page_content="P0420 info", metadata={"type": "dtc", "code": "P0420"})
        trace = RetrievalTrace(query="q", hits=[])
        mock_kb.retrieve_detailed.return_value = ([(doc, 0.9)], trace)
        with patch.object(rag_tool, "_kb", lambda: mock_kb):
            retrieve_for_codes(["P0420"], filter_by_type=True)
        mock_kb.retrieve_detailed.assert_called_once()
        assert mock_kb.retrieve_detailed.call_args.kwargs.get("filter_dict") == {"type": "dtc"}

    def test_prefers_make_when_provided(self):
        generic = Document(
            page_content="generic P0420",
            metadata={"type": "dtc", "code": "P0420", "make": "generic"},
        )
        toyota = Document(
            page_content="Toyota P0420",
            metadata={"type": "dtc", "code": "P0420", "make": "Toyota"},
        )
        mock_kb = MagicMock()
        mock_kb.lookup_dtc_code.return_value = None
        trace = RetrievalTrace(query="q", hits=[])
        mock_kb.retrieve_detailed.return_value = ([(generic, 0.5), (toyota, 0.4)], trace)
        with patch.object(rag_tool, "_kb", lambda: mock_kb):
            out = retrieve_for_codes(["P0420"], make="Toyota", filter_by_type=True)
        assert "Toyota" in out or "P0420" in out
