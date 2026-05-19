"""Shared pytest fixtures for Agentic Workflow tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def _use_fake_embeddings_for_tests():
    """Avoid loading sentence-transformers during pytest (Py3.13 Windows crash)."""
    os.environ["RAG_USE_FAKE_EMBEDDINGS"] = "1"
    os.environ["RAG_RERANK_ENABLED"] = "0"
    os.environ["RAG_HYBRID_ENABLED"] = "0"
    yield


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture(scope="session")
def dtc_sample_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "dtc_sample.json"


@pytest.fixture(scope="session")
def manual_sample_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "manual_sample.pdf"


def embeddings_available() -> bool:
    import importlib.util
    import platform
    import sys

    if sys.version_info >= (3, 13) and platform.system() == "Windows":
        return False
    try:
        return importlib.util.find_spec("sentence_transformers") is not None
    except Exception:
        return False


@pytest.fixture(scope="session")
def require_embeddings():
    if not embeddings_available():
        pytest.skip("sentence-transformers unavailable (use Python 3.11/3.12 on Windows)")
