"""Unit tests for RAG ingest parsers (SC-04, SC-05)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.rag.ingest.parsers import (
    DTC_REQUIRED_META,
    dtc_row_to_document,
    load_dtc_json,
    parse_manual_pdf,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestDtcParser:
    def test_all_fixture_rows_produce_required_metadata(self, dtc_sample_path: Path):
        rows = json.loads(dtc_sample_path.read_text(encoding="utf-8"))
        assert len(rows) >= 10
        for row in rows:
            doc = dtc_row_to_document(row)
            for key in DTC_REQUIRED_META:
                assert key in doc.metadata, f"missing {key} for {row.get('code')}"
            assert doc.metadata["type"] == "dtc"
            assert doc.page_content

    def test_code_normalized_uppercase(self):
        doc = dtc_row_to_document({"code": "p0420", "description": "test", "make": "generic"})
        assert doc.metadata["code"] == "P0420"

    def test_load_dtc_json_respects_max_rows(self, dtc_sample_path: Path):
        docs = load_dtc_json(dtc_sample_path, max_rows=3)
        assert len(docs) == 3

    def test_load_dtc_json_brand_filter(self, dtc_sample_path: Path):
        docs = load_dtc_json(dtc_sample_path, brands=["Toyota"])
        assert all(
            d.metadata["make"].lower() in ("toyota", "generic") for d in docs
        )

    def test_missing_code_raises(self):
        with pytest.raises(ValueError):
            dtc_row_to_document({"description": "no code"})

    def test_system_inferred_from_prefix(self):
        doc = dtc_row_to_document({"code": "C0750", "description": "x", "make": "generic"})
        assert doc.metadata["system"] == "chassis"

    def test_p_code_powertrain(self):
        doc = dtc_row_to_document({"code": "P0301", "description": "misfire", "make": "generic"})
        assert doc.metadata["system"] == "powertrain"


class TestManualParser:
    def test_manual_sample_yields_manual_type(self, manual_sample_path: Path):
        docs = parse_manual_pdf(manual_sample_path, make="TestMake", model="TestModel", year=2020)
        assert len(docs) >= 1
        assert all(d.metadata.get("type") == "manual" for d in docs)
        assert all(d.page_content.strip() for d in docs)

    def test_manual_metadata_fields(self, manual_sample_path: Path):
        docs = parse_manual_pdf(manual_sample_path, make="Toyota", model="Camry", year=2020)
        meta = docs[0].metadata
        assert meta["make"] == "Toyota"
        assert meta["model"] == "Camry"
        assert meta["year"] == 2020
        assert "page" in meta

    def test_tire_pressure_text_present(self, manual_sample_path: Path):
        docs = parse_manual_pdf(manual_sample_path, make="Test", model="M", year=2020)
        combined = " ".join(d.page_content for d in docs).lower()
        assert "psi" in combined or "tire" in combined
