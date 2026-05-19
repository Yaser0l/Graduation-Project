"""Live network tests — not run in default CI (@pytest.mark.live)."""
from __future__ import annotations

import pytest

from pathlib import Path

ROOT = Path(__file__).parent.parent


@pytest.mark.live
@pytest.mark.integration
def test_download_dtc_only(tmp_path, require_embeddings):
    from src.rag.ingest.download import run_download

    sources = tmp_path / "sources"
    run_download(
        ROOT,
        sources,
        ROOT / "data" / "sources" / "brand_sources.yaml",
        download_dtc=True,
        download_manuals_flag=False,
    )
    dtc_files = list((sources / "dtc").glob("*.json"))
    assert dtc_files, "expected at least one DTC json file"
