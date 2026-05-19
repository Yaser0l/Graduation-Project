"""Tests for generic DTC-list PDF parsing."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.rag.ingest.parsers import load_dtc_pdf

ROOT = Path(__file__).resolve().parent.parent
DTC_LIST = ROOT / "data" / "sources" / "dtc" / "dtc_list.pdf"


def test_load_dtc_pdf_extracts_codes():
    if not DTC_LIST.exists():
        pytest.skip("data/sources/dtc/dtc_list.pdf not present")
    docs = load_dtc_pdf(DTC_LIST)
    codes = {d.metadata["code"] for d in docs}
    assert len(codes) >= 400
    assert "P0420" in codes or "P0100" in codes
    assert all(d.metadata["type"] == "dtc" for d in docs)
    assert all(d.metadata["make"] == "generic" for d in docs)
