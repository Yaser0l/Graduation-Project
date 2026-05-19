"""Production RAG ingest policy (2025–2026 best practices for automotive KB).

Ingest: atomic DTC, section-aware manual chunks with parent_id (see manual_chunking.py).
Query: hybrid BM25+dense (RRF) + cross-encoder rerank (see knowledge_base.py).
"""
from __future__ import annotations

# DTC: do not split — each Document is one OBD-II code (retrieval precision).
RAG_DTC_ATOMIC_CHUNKS = True

# Manuals: section-aware splits, then ~1k chars / ~20% overlap within each section.
RAG_MANUAL_CHUNK_SIZE = 1000
RAG_MANUAL_CHUNK_OVERLAP = 200

# Wal33D SQLite is primary; supplemental PDFs (e.g. generic DTC lists) fill gaps only.
DTC_SOURCE_PRIORITY = ("dtc_codes.db", "*.db", "*.json", "dtc_list.pdf", "*.pdf")
