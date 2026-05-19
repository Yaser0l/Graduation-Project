"""Download DTC databases and OEM owner manuals."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import yaml

from src.rag.sources import get_adapter
from src.rag.sources.catalog_adapter import CatalogAdapter

MANUAL_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/octet-stream,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Pinned fallback: small MIT JSON repo
FABIOLA_DTC_URL = (
    "https://raw.githubusercontent.com/fabiovila/OBDIICodes/master/codes.json"
)
WAL33D_DTC_DB_URL = (
    "https://github.com/Wal33D/dtc-database/raw/main/data/dtc_codes.db"
)


def _fetch_pdf_to_file(
    client: httpx.Client, url: str, dest: Path, *, headers: dict, attempts: int = 3
) -> None:
    """Stream a PDF to disk with retries (large OEM manuals, e.g. Ford ~8MB)."""
    last_err: Exception | None = None
    for attempt in range(attempts):
        try:
            with client.stream(
                "GET", url, headers=headers, follow_redirects=True, timeout=600.0
            ) as response:
                response.raise_for_status()
                first = b""
                with dest.open("wb") as fh:
                    for chunk in response.iter_bytes(chunk_size=65536):
                        if not first and chunk:
                            first = chunk[:4]
                        fh.write(chunk)
                if not first.startswith(b"%PDF"):
                    dest.unlink(missing_ok=True)
                    raise ValueError(
                        f"Response is not a PDF (starts with {first!r}, "
                        f"content-type={response.headers.get('content-type', '')})"
                    )
            return
        except Exception as exc:
            last_err = exc
            dest.unlink(missing_ok=True)
            if attempt + 1 < attempts:
                continue
    raise last_err  # type: ignore[misc]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_file(url: str, dest: Path, client: httpx.Client, force: bool = False) -> Dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        return {
            "kind": "dtc",
            "path": str(dest),
            "url": url,
            "sha256": _sha256_file(dest),
            "status": "skipped",
        }
    try:
        response = client.get(url, follow_redirects=True)
        response.raise_for_status()
        dest.write_bytes(response.content)
        return {
            "kind": "dtc",
            "path": str(dest),
            "url": url,
            "sha256": _sha256_file(dest),
            "status": "ok",
        }
    except Exception as exc:
        return {
            "kind": "dtc",
            "path": str(dest),
            "url": url,
            "status": "failed",
            "error": str(exc),
        }


def download_dtc_database(dtc_dir: Path, client: httpx.Client, force: bool = False) -> Dict[str, Any]:
    """Download DTC data; try Wal33D SQLite then fabiovila JSON fallback."""
    dtc_dir.mkdir(parents=True, exist_ok=True)
    dest = dtc_dir / "dtc_codes.db"
    result = _download_file(WAL33D_DTC_DB_URL, dest, client, force=force)
    if result.get("status") != "failed":
        result["kind"] = "dtc"
        return result
    fallback_dest = dtc_dir / "codes.json"
    result = _download_file(FABIOLA_DTC_URL, fallback_dest, client, force=force)
    return result


def load_brand_config(path: Path) -> List[Dict[str, Any]]:
    """Load brand_sources.yaml brands list."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return list(data.get("brands") or [])


def download_manuals(
    brand_config_path: Path,
    manuals_root: Path,
    client: httpx.Client,
    force: bool = False,
    brands_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Download owner manuals for vehicles listed in brand config."""
    entries = load_brand_config(brand_config_path)
    brand_set = {b.lower() for b in brands_filter} if brands_filter else None
    results: List[Dict[str, Any]] = []

    for entry in entries:
        make = str(entry["make"])
        model = str(entry["model"])
        year = int(entry["year"])
        adapter_name = str(entry.get("adapter") or make.lower())

        if brand_set and make.lower() not in brand_set:
            continue

        dest_dir = manuals_root / make / model / str(year)
        dest = dest_dir / "owner_manual.pdf"
        dest_dir.mkdir(parents=True, exist_ok=True)

        if dest.exists() and not force:
            results.append(
                {
                    "kind": "manual",
                    "path": str(dest),
                    "make": make,
                    "model": model,
                    "year": year,
                    "sha256": _sha256_file(dest),
                    "status": "skipped",
                }
            )
            continue

        adapter = get_adapter(adapter_name)
        try:
            url = adapter.resolve_manual_url(make, model, year)
            if not url:
                raise ValueError("adapter returned empty URL")
            headers = dict(MANUAL_HTTP_HEADERS)
            if isinstance(adapter, CatalogAdapter):
                referer = adapter.resolve_referer(make, model, year)
                if referer:
                    headers["Referer"] = referer
            _fetch_pdf_to_file(client, url, dest, headers=headers)
            publisher = ""
            if isinstance(adapter, CatalogAdapter):
                entry = adapter.resolve_manual(make, model, year)
                publisher = entry.publisher
            results.append(
                {
                    "kind": "manual",
                    "path": str(dest),
                    "url": url,
                    "make": make,
                    "model": model,
                    "year": year,
                    "publisher": publisher,
                    "sha256": _sha256_file(dest),
                    "status": "ok",
                }
            )
        except Exception as exc:
            results.append(
                {
                    "kind": "manual",
                    "path": str(dest),
                    "make": make,
                    "model": model,
                    "year": year,
                    "status": "failed",
                    "error": str(exc),
                }
            )
    return results


def copy_fixture_sources(fixtures_dir: Path, dtc_dir: Path, manuals_root: Path) -> List[Dict[str, Any]]:
    """Copy test fixtures into source layout for --fixtures-dir mode."""
    sources: List[Dict[str, Any]] = []
    dtc_src = fixtures_dir / "dtc_sample.json"
    if dtc_src.exists():
        dtc_dir.mkdir(parents=True, exist_ok=True)
        dest = dtc_dir / "dtc_sample.json"
        shutil.copy2(dtc_src, dest)
        sources.append(
            {
                "kind": "dtc",
                "path": str(dest),
                "sha256": _sha256_file(dest),
                "status": "ok",
            }
        )
    manual_src = fixtures_dir / "manual_sample.pdf"
    if manual_src.exists():
        dest_dir = manuals_root / "TestMake" / "TestModel" / "2020"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "owner_manual.pdf"
        shutil.copy2(manual_src, dest)
        sources.append(
            {
                "kind": "manual",
                "path": str(dest),
                "make": "TestMake",
                "model": "TestModel",
                "year": 2020,
                "sha256": _sha256_file(dest),
                "status": "ok",
            }
        )
    return sources


def write_manifest(manifest_path: Path, sources: List[Dict[str, Any]], stats: Optional[Dict[str, Any]] = None) -> None:
    """Write manifest.json for ingest run."""
    payload = {
        "version": "1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "stats": stats or {},
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_download(
    project_root: Path,
    sources_dir: Path,
    brand_config_path: Path,
    *,
    force: bool = False,
    brands: Optional[List[str]] = None,
    fixtures_dir: Optional[Path] = None,
    download_dtc: bool = True,
    download_manuals_flag: bool = True,
) -> List[Dict[str, Any]]:
    """Execute download phase; returns manifest source entries."""
    dtc_dir = sources_dir / "dtc"
    manuals_root = sources_dir / "manuals"
    all_sources: List[Dict[str, Any]] = []

    if fixtures_dir:
        all_sources.extend(copy_fixture_sources(fixtures_dir, dtc_dir, manuals_root))
        write_manifest(sources_dir / "manifest.json", all_sources)
        return all_sources

    with httpx.Client(timeout=60.0, headers=MANUAL_HTTP_HEADERS) as client:
        if download_dtc:
            all_sources.append(download_dtc_database(dtc_dir, client, force=force))
        if download_manuals_flag and brand_config_path.exists():
            all_sources.extend(
                download_manuals(brand_config_path, manuals_root, client, force=force, brands_filter=brands)
            )

    write_manifest(sources_dir / "manifest.json", all_sources)
    return all_sources
