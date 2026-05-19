"""Unit tests for download + manifest (SC-06, SC-07)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.rag.ingest.download import (
    _sha256_file,
    copy_fixture_sources,
    download_dtc_database,
    write_manifest,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestManifest:
    def test_manifest_matches_schema(self, tmp_path: Path):
        manifest_path = tmp_path / "manifest.json"
        sources = [
            {"kind": "dtc", "path": "/a.json", "status": "ok", "sha256": "abc"},
            {"kind": "manual", "path": "/b.pdf", "status": "skipped", "make": "Toyota"},
        ]
        write_manifest(manifest_path, sources, stats={"chunks_indexed": 10})
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        schema = json.loads((FIXTURES / "manifest_schema.json").read_text(encoding="utf-8"))
        assert data["version"] == "1"
        assert "created_at" in data
        assert len(data["sources"]) == 2
        required = schema["properties"]["sources"]["items"]["required"]
        for entry in data["sources"]:
            for key in required:
                assert key in entry


class TestDownloadIdempotency:
    def test_dtc_skip_when_exists(self, tmp_path: Path):
        dtc_dir = tmp_path / "dtc"
        dtc_dir.mkdir()
        dest = dtc_dir / "dtc_codes.db"
        dest.write_bytes(b"SQLite format 3\x00")

        client = MagicMock(spec=httpx.Client)
        result = download_dtc_database(dtc_dir, client, force=False)
        assert result["status"] == "skipped"
        client.get.assert_not_called()

    def test_dtc_force_redownloads(self, tmp_path: Path):
        dtc_dir = tmp_path / "dtc"
        dtc_dir.mkdir()
        dest = dtc_dir / "dtc_codes.db"
        dest.write_bytes(b"old")

        mock_response = MagicMock()
        mock_response.content = b'{"codes":[{"code":"P0420","description":"test","make":"generic"}]}'
        mock_response.raise_for_status = MagicMock()

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        with patch("src.rag.ingest.download.WAL33D_DTC_DB_URL", "http://example.com/dtc.db"):
            result = download_dtc_database(dtc_dir, client, force=True)
        assert result["status"] == "ok"
        assert client.get.call_count >= 1

    def test_sha256_stable(self, tmp_path: Path):
        f = tmp_path / "f.txt"
        f.write_text("hello", encoding="utf-8")
        assert _sha256_file(f) == _sha256_file(f)


class TestFixtureCopy:
    def test_copy_fixture_sources(self, tmp_path: Path):
        sources = copy_fixture_sources(FIXTURES, tmp_path / "dtc", tmp_path / "manuals")
        kinds = {s["kind"] for s in sources}
        assert "dtc" in kinds
        assert "manual" in kinds
        assert (tmp_path / "dtc" / "dtc_sample.json").exists()
        assert (tmp_path / "manuals" / "TestMake" / "TestModel" / "2020" / "owner_manual.pdf").exists()
