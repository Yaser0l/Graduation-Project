"""CLI subprocess tests (SC-15)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "ingest_rag_full.py"


class TestIngestCli:
    def test_help_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "ingest" in result.stdout.lower() or "RAG" in result.stdout

    def test_fixtures_skip_download_reset(self, tmp_path):
        chroma = tmp_path / "chroma"
        sources = tmp_path / "sources"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--fixtures-dir",
                "tests/fixtures",
                "--skip-download",
                "--reset",
                "--skip-preflight",
                "--sources-dir",
                str(sources),
                "--chroma-dir",
                str(chroma),
                "--quiet",
                "--fake-embeddings",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, result.stderr + result.stdout
