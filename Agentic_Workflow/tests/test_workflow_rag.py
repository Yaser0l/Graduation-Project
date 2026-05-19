"""RAG section of workflow tests (SC-21) — no LLM calls."""
from __future__ import annotations

from src.rag.knowledge_base import AutomotiveKnowledgeBase


def test_rag_retrieve_and_reflect(tmp_path):
    kb = AutomotiveKnowledgeBase(persist_directory=str(tmp_path / "chroma"))
    kb.initialize_with_sample_data()

    docs = kb.retrieve("C0750 tire pressure sensor", k=3)
    assert docs
    assert any("C0750" in d.page_content or d.metadata.get("code") == "C0750" for d in docs)

    is_sufficient, score, reflection = kb.reflect_on_retrieval("C0750 tire pressure sensor", docs)
    assert isinstance(is_sufficient, bool)
    assert score >= 0.0
    assert reflection
