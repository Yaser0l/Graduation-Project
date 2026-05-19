"""Knowledge base tests (SC-03)."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from langchain_core.documents import Document

from tests.fake_embeddings import FakeEmbeddings

ROOT = Path(__file__).resolve().parent.parent


class TestNoAutoSeed:
    def test_import_does_not_auto_seed(self, tmp_path, monkeypatch):
        """Importing knowledge_base must not populate an empty Chroma DB."""
        chroma = tmp_path / "empty_chroma"
        monkeypatch.setenv("CHROMA_DB_PATH", str(chroma))
        if "src.rag.knowledge_base" in sys.modules:
            del sys.modules["src.rag.knowledge_base"]
        mod = importlib.import_module("src.rag.knowledge_base")
        kb = mod.AutomotiveKnowledgeBase(
            persist_directory=str(chroma),
            embedding_function=FakeEmbeddings(),
        )
        assert kb.get_collection_count() == 0


class TestKnowledgeBaseOps:
    def test_reset_collection_clears_and_reindexes(self, tmp_path):
        from src.rag.knowledge_base import AutomotiveKnowledgeBase

        kb = AutomotiveKnowledgeBase(
            persist_directory=str(tmp_path / "chroma"),
            embedding_function=FakeEmbeddings(),
        )
        kb.add_documents([
            Document(page_content="P0420 catalyst test", metadata={"type": "dtc", "code": "P0420", "make": "generic"}),
        ])
        assert kb.get_collection_count() >= 1
        kb.reset_collection()
        assert kb.get_collection_count() == 0
        kb.add_documents([
            Document(page_content="P0420 after reset", metadata={"type": "dtc", "code": "P0420", "make": "generic"}),
        ])
        assert kb.get_collection_count() >= 1

    def test_get_stats_counts_types(self, tmp_path):
        from src.rag.knowledge_base import AutomotiveKnowledgeBase

        kb = AutomotiveKnowledgeBase(
            persist_directory=str(tmp_path / "chroma2"),
            embedding_function=FakeEmbeddings(),
        )
        kb.reset_collection()
        kb.add_documents([
            Document(page_content="DTC one", metadata={"type": "dtc", "code": "P0420", "make": "Toyota"}),
            Document(page_content="Manual tire PSI 32-35", metadata={"type": "manual", "make": "Toyota"}),
        ])
        stats = kb.get_stats()
        assert stats["total_chunks"] >= 2
        assert stats["dtc"] >= 1
        assert stats["manual"] >= 1

    def test_retrieve_with_filter(self, tmp_path):
        from src.rag.knowledge_base import AutomotiveKnowledgeBase

        kb = AutomotiveKnowledgeBase(
            persist_directory=str(tmp_path / "chroma3"),
            embedding_function=FakeEmbeddings(),
        )
        kb.reset_collection()
        kb.add_documents([
            Document(
                page_content="P0420 Catalyst efficiency below threshold bank 1",
                metadata={"type": "dtc", "code": "P0420", "make": "generic"},
            ),
            Document(
                page_content="Tire pressure recommended 32 PSI cold",
                metadata={"type": "manual", "make": "Test"},
            ),
        ])
        dtc_docs = kb.retrieve("P0420 catalyst", k=3, filter_dict={"type": "dtc"})
        assert dtc_docs
        assert all(d.metadata.get("type") == "dtc" for d in dtc_docs)
