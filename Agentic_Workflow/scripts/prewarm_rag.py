#!/usr/bin/env python3
"""Prewarm RAG assets during image build.

- Optionally download a prebuilt dataset from Hugging Face into ./data
- Initialize Chroma with sample data if empty
- Preload the embedding model to cache weights
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config


def _is_db_empty() -> bool:
    db_path = Path(config.CHROMA_DB_PATH)
    sqlite_file = db_path / "chroma.sqlite3"
    return not sqlite_file.exists() or sqlite_file.stat().st_size == 0


def _strict_mode() -> bool:
    return os.getenv("RAG_PREWARM_STRICT", "0").strip().lower() in ("1", "true", "yes")


def _download_dataset_if_needed() -> bool:
    if not _is_db_empty():
        return False

    token = (
        os.getenv("HF_TOKEN", "").strip()
        or os.getenv("HUGGING_FACE_HUB_TOKEN", "").strip()
    )
    if not token:
        logging.info("HF_TOKEN not set; skipping dataset download.")
        return False

    repo_id = os.getenv("HF_DATASET_REPO", "aziz9788/automotive-rag-kb").strip()
    logging.info("Downloading prebuilt dataset from HF: %s", repo_id)

    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:
        logging.error("huggingface_hub is required for dataset download: %s", exc)
        return False

    data_dir = Path(config.CHROMA_DB_PATH).parent
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            local_dir=str(data_dir),
            token=token,
            allow_patterns=["chroma_db/**", "sources/**"],
        )
        return True
    except Exception as exc:
        logging.error("Dataset download failed: %s", exc)
        return False


def _initialize_kb() -> None:
    from src.rag.knowledge_base import knowledge_base

    if _is_db_empty() or knowledge_base.get_collection_count() == 0:
        logging.info("RAG database is empty; seeding with sample DTC data.")
        knowledge_base.initialize_with_sample_data()
        logging.info(
            "Sample data initialized. Chunk count: %d",
            knowledge_base.get_collection_count(),
        )
    else:
        logging.info(
            "RAG database loaded. Chunk count: %d",
            knowledge_base.get_collection_count(),
        )

    try:
        _ = knowledge_base.embeddings
        logging.info("Embedding model preloaded.")
    except Exception as exc:
        logging.error("Embedding preload failed: %s", exc)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    _download_dataset_if_needed()
    _initialize_kb()

    if _strict_mode() and _is_db_empty():
        raise RuntimeError("RAG data missing after prewarm; check dataset or ingest settings.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
