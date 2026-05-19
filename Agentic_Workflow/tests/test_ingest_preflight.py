"""Unit tests for preflight checks (SC-08, SC-09)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from src.rag.ingest.preflight import (
    EXIT_PREFLIGHT_FAIL,
    check_embeddings_import,
    run_preflight,
)


class TestPreflight:
    def test_preflight_passes_with_deps(self, tmp_path: Path):
        kwargs = {}
        if sys.version_info >= (3, 13) and __import__("platform").system() == "Windows":
            kwargs["skip_embeddings"] = True
        result = run_preflight(tmp_path, tmp_path / "sources", tmp_path / "chroma", **kwargs)
        assert result.ok
        assert result.exit_code == 0

    def test_missing_pypdf_reported(self, tmp_path: Path):
        with patch("src.rag.ingest.preflight._check_import") as mock_import:
            def side_effect(module, pip_name=None):
                if module == "pypdf":
                    return "Missing dependency 'pypdf'. Install with: pip install pypdf"
                return None
            mock_import.side_effect = side_effect
            result = run_preflight(tmp_path, tmp_path / "sources", tmp_path / "chroma")
        assert not result.ok
        assert result.exit_code == EXIT_PREFLIGHT_FAIL
        assert any("pypdf" in m.lower() for m in result.messages)

    def test_embeddings_check_when_package_missing(self):
        with patch("src.rag.ingest.preflight.importlib.util.find_spec", return_value=None):
            msg = check_embeddings_import()
        assert msg is not None
        assert "sentence-transformers" in msg.lower()

    def test_embeddings_check_fastembed_backend(self):
        with patch.dict("os.environ", {"RAG_EMBEDDING_BACKEND": "fastembed"}, clear=False):
            with patch("src.rag.ingest.preflight.importlib.util.find_spec", return_value=object()):
                msg = check_embeddings_import()
        assert msg is None

    def test_skip_embeddings_flag(self, tmp_path: Path):
        with patch("src.rag.ingest.preflight.check_embeddings_import", return_value="fail"):
            result = run_preflight(
                tmp_path, tmp_path / "sources", tmp_path / "chroma", skip_embeddings=True
            )
        assert result.ok
