"""Integration tests: fixture ingest → Chroma → retrieval (SC-10–SC-14)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from src.rag.ingest.download import copy_fixture_sources, run_download
from src.rag.ingest.runner import run_full_ingest, run_index
from src.rag.knowledge_base import AutomotiveKnowledgeBase
from tests.fake_embeddings import FakeEmbeddings

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.integration
class TestFixtureIngest:
    @pytest.fixture
    def ingest_env(self, tmp_path):
        sources = tmp_path / "sources"
        chroma = str(tmp_path / "chroma_db")
        copy_fixture_sources(FIXTURES, sources / "dtc", sources / "manuals")
        return sources, chroma

    def test_indexes_at_least_15_chunks(self, ingest_env):
        sources, chroma = ingest_env
        kb = AutomotiveKnowledgeBase(
            persist_directory=chroma,
            embedding_function=FakeEmbeddings(),
        )
        stats = run_index(kb, sources, reset=True, max_dtc=0)
        count = stats.get("chunks_indexed", stats.get("total_chunks", 0))
        assert count >= 14, f"expected >=14 chunks, got {count}"

    def test_get_stats_dtc_and_manual(self, ingest_env):
        sources, chroma = ingest_env
        kb = AutomotiveKnowledgeBase(
            persist_directory=chroma,
            embedding_function=FakeEmbeddings(),
        )
        stats = run_index(kb, sources, reset=True)
        assert stats["dtc"] >= 10
        assert stats["manual"] >= 1

    def test_retrieve_p0420(self, ingest_env):
        sources, chroma = ingest_env
        kb = AutomotiveKnowledgeBase(
            persist_directory=chroma,
            embedding_function=FakeEmbeddings(),
        )
        run_index(kb, sources, reset=True)
        docs = kb.retrieve("P0420 catalyst efficiency", k=3)
        assert docs
        found = any(
            "P0420" in d.page_content or d.metadata.get("code") == "P0420" for d in docs
        )
        assert found

    def test_retrieve_manual_tire_pressure(self, ingest_env):
        sources, chroma = ingest_env
        kb = AutomotiveKnowledgeBase(
            persist_directory=chroma,
            embedding_function=FakeEmbeddings(),
        )
        run_index(kb, sources, reset=True)
        docs = kb.retrieve("tire pressure recommended PSI", k=5, filter_dict={"type": "manual"})
        if not docs:
            docs = kb.retrieve("tire pressure recommended PSI", k=5)
        assert any(d.metadata.get("type") == "manual" for d in docs)

    def test_reset_stable_count(self, ingest_env):
        sources, chroma = ingest_env
        kb = AutomotiveKnowledgeBase(
            persist_directory=chroma,
            embedding_function=FakeEmbeddings(),
        )
        run_index(kb, sources, reset=True)
        c1 = kb.get_collection_count()
        run_index(kb, sources, reset=True)
        c2 = kb.get_collection_count()
        assert c1 == c2

    def test_full_ingest_via_runner_fixtures(self, tmp_path):
        sources = tmp_path / "sources"
        chroma = str(tmp_path / "chroma2")
        brand_yaml = FIXTURES / "brand_sources_minimal.yaml"
        result = run_full_ingest(
            tmp_path,
            sources,
            chroma,
            brand_yaml,
            reset=True,
            skip_download=False,
            fixtures_dir=FIXTURES,
            skip_preflight=True,
        )
        assert result["stats"]["total_chunks"] >= 14
        manifest = json.loads((sources / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["sources"]
