"""Orchestrate download + index phases for RAG ingestion."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.rag.knowledge_base import AutomotiveKnowledgeBase

from langchain_core.documents import Document

from src.rag.ingest.download import copy_fixture_sources, run_download, write_manifest
from src.rag.ingest.parsers import load_all_sources
from src.rag.ingest.preflight import run_preflight

logger = logging.getLogger(__name__)


def find_dtc_file(dtc_dir: Path) -> Optional[Path]:
    if not dtc_dir.exists():
        return None
    for name in ("dtc_codes.db", "dtc_database.json", "dtc_sample.json", "codes.json", "obd2_codes.json"):
        candidate = dtc_dir / name
        if candidate.exists():
            return candidate
    db_files = list(dtc_dir.glob("*.db"))
    if db_files:
        return db_files[0]
    json_files = list(dtc_dir.glob("*.json"))
    return json_files[0] if json_files else None


def index_documents(
    kb: "AutomotiveKnowledgeBase",
    documents: List[Document],
    *,
    reset: bool = False,
) -> int:
    """Index documents into Chroma; returns chunk count after ingest."""
    if reset:
        kb.reset_collection()
    if not documents:
        return 0
    kb.add_documents(documents)
    return kb.get_collection_count()


def run_index(
    kb: "AutomotiveKnowledgeBase",
    sources_dir: Path,
    *,
    reset: bool = False,
    max_dtc: int = 0,
    brands: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Load sources from disk and index into the knowledge base."""
    dtc_dir = sources_dir / "dtc"
    manuals_root = sources_dir / "manuals"
    documents = load_all_sources(dtc_dir, manuals_root, max_dtc=max_dtc, brands=brands)
    chunk_count = index_documents(kb, documents, reset=reset)
    stats = kb.get_stats()
    stats["chunks_indexed"] = chunk_count
    stats["source_documents"] = len(documents)
    return stats


def run_full_ingest(
    project_root: Path,
    sources_dir: Path,
    chroma_dir: str,
    brand_config_path: Path,
    *,
    reset: bool = False,
    skip_download: bool = False,
    download_only: bool = False,
    force: bool = False,
    brands: Optional[List[str]] = None,
    max_dtc: int = 0,
    fixtures_dir: Optional[Path] = None,
    skip_preflight: bool = False,
    embedding_function: Optional[Any] = None,
) -> Dict[str, Any]:
    """Run preflight, optional download, and optional index."""
    if not skip_preflight:
        pre = run_preflight(project_root, sources_dir, Path(chroma_dir))
        if not pre.ok:
            raise RuntimeError("\n".join(pre.messages))

    manifest_sources: List[Dict[str, Any]] = []
    if fixtures_dir and skip_download:
        dtc_dir = sources_dir / "dtc"
        manuals_dir = sources_dir / "manuals"
        copy_fixture_sources(fixtures_dir, dtc_dir, manuals_dir)
        manifest_sources = [{"kind": "fixture", "status": "ok", "path": str(fixtures_dir)}]
    elif not skip_download:
        manifest_sources = run_download(
            project_root,
            sources_dir,
            brand_config_path,
            force=force,
            brands=brands,
            fixtures_dir=fixtures_dir,
        )

    if download_only:
        return {"phase": "download", "sources": manifest_sources}

    from src.rag.knowledge_base import AutomotiveKnowledgeBase, resolve_embedding_function

    kb = AutomotiveKnowledgeBase(
        persist_directory=chroma_dir,
        embedding_function=resolve_embedding_function(embedding_function),
    )
    stats = run_index(kb, sources_dir, reset=reset, max_dtc=max_dtc, brands=brands)
    write_manifest(sources_dir / "manifest.json", manifest_sources, stats=stats)
    return {"phase": "full", "sources": manifest_sources, "stats": stats}
