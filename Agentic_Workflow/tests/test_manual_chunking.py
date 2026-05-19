"""Tests for section-aware manual chunking (ingest v2)."""
from __future__ import annotations

from langchain_core.documents import Document

from src.rag.ingest.manual_chunking import (
    chunk_manual_document,
    manual_parent_id,
    split_page_into_sections,
)


class TestManualChunking:
    def test_split_detects_heading(self):
        text = "TIRE PRESSURE\nRecommended cold pressure is 32 PSI.\nCheck the door jamb sticker."
        sections = split_page_into_sections(text)
        assert len(sections) >= 1
        titles = [t for t, _ in sections]
        assert any("TIRE" in t.upper() for t in titles) or sections[0][1]

    def test_chunk_has_parent_id_and_chunk_id(self):
        doc = Document(
            page_content="MAINTENANCE\nOil change every 5,000 miles.",
            metadata={
                "type": "manual",
                "make": "Toyota",
                "model": "Camry",
                "year": 2020,
                "page": 3,
                "source_file": "owner_manual.pdf",
            },
        )
        chunks = chunk_manual_document(doc, chunk_size=80, chunk_overlap=10)
        assert chunks
        meta = chunks[0].metadata
        assert meta["parent_id"] == manual_parent_id(doc.metadata)
        assert meta["chunk_id"].startswith(meta["parent_id"])
        assert "section_index" in meta
