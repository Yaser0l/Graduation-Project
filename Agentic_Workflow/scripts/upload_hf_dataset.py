#!/usr/bin/env python3
"""Upload RAG databases (Chroma + sources) to a private Hugging Face dataset repo.

Requires HF_TOKEN in .env or environment (write access).

Usage:
    python scripts/upload_hf_dataset.py
    python scripts/upload_hf_dataset.py --repo-id YOUR_USER/automotive-rag-kb
    python scripts/upload_hf_dataset.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

DATA_ROOT = PROJECT_ROOT / "data"
DEFAULT_README = """---
license: mit
task_categories:
  - feature-extraction
language:
  - en
tags:
  - automotive
  - rag
  - obd2
  - dtc
  - owner-manuals
---

# Automotive RAG knowledge base (Graduation Project)

Private dataset backing the Agentic Workflow RAG pipeline.

## Contents

| Path | Description |
|------|-------------|
| `chroma_db/` | Chroma vector store (BGE embeddings, ~38k chunks) |
| `chroma_db/bm25_index.pkl` | BM25 lexical index for hybrid retrieval |
| `sources/dtc/` | Wal33D SQLite + supplemental DTC PDFs |
| `sources/manuals/` | OEM owner manual PDFs (per make/model/year) |
| `sources/manifest.json` | Ingest manifest with sha256 |
| `sources/brand_sources.yaml` | Download registry |

## Restore locally

```bash
# Install: pip install huggingface_hub
huggingface-cli download REPO_ID --repo-type dataset --local-dir ./data --token $HF_TOKEN
```

Then point `CHROMA_DB_PATH=./data/chroma_db` and `RAG_SOURCES_DIR=./data/sources`.
"""


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Upload Agentic_Workflow data/ to Hugging Face Hub")
    p.add_argument(
        "--repo-id",
        default=os.getenv("HF_DATASET_REPO", "").strip(),
        help="Dataset repo id (user/name). Default: HF_DATASET_REPO or {whoami}/automotive-rag-kb",
    )
    p.add_argument("--private", action="store_true", default=True)
    p.add_argument("--public", action="store_true", help="Make dataset public (default: private)")
    p.add_argument("--dry-run", action="store_true", help="List files only, no upload")
    p.add_argument("--skip-chroma", action="store_true")
    p.add_argument("--skip-sources", action="store_true")
    return p.parse_args()


def _collect_paths(skip_chroma: bool, skip_sources: bool) -> list[tuple[Path, str]]:
    """Return (local_path, path_in_repo) pairs."""
    pairs: list[tuple[Path, str]] = []
    if not skip_chroma:
        chroma = DATA_ROOT / "chroma_db"
        if chroma.is_dir():
            pairs.append((chroma, "chroma_db"))
    if not skip_sources:
        sources = DATA_ROOT / "sources"
        for sub in ("dtc", "manuals"):
            local = sources / sub
            if local.is_dir():
                pairs.append((local, f"sources/{sub}"))
        for name in ("manifest.json", "brand_sources.yaml", "README.md", "INGEST_BEST_PRACTICES.md"):
            f = sources / name
            if f.is_file():
                pairs.append((f, f"sources/{name}"))
    return pairs


def main() -> int:
    args = _parse_args()
    token = (
        os.getenv("HF_TOKEN", "").strip()
        or os.getenv("HUGGING_FACE_HUB_TOKEN", "").strip()
    )
    if not token:
        print("ERROR: Set HF_TOKEN in .env (write access).", file=sys.stderr)
        return 2

    try:
        from huggingface_hub import HfApi, create_repo, whoami
    except ImportError:
        print("ERROR: pip install huggingface_hub", file=sys.stderr)
        return 2

    user = whoami(token=token).get("name") or whoami(token=token).get("username")
    repo_id = args.repo_id or os.getenv("HF_DATASET_REPO") or f"{user}/automotive-rag-kb"
    private = not args.public

    uploads = _collect_paths(args.skip_chroma, args.skip_sources)
    if not uploads:
        print("ERROR: Nothing to upload under data/", file=sys.stderr)
        return 2

    total_bytes = 0
    file_count = 0
    for local, _ in uploads:
        if local.is_file():
            total_bytes += local.stat().st_size
            file_count += 1
        else:
            for f in local.rglob("*"):
                if f.is_file():
                    total_bytes += f.stat().st_size
                    file_count += 1

    print(f"HF user: {user}")
    print(f"Dataset: {repo_id} (private={private})")
    print(f"Upload bundles: {len(uploads)} | ~{file_count} files | ~{total_bytes / (1024**2):.1f} MB")

    for local, remote in uploads:
        print(f"  {local.relative_to(PROJECT_ROOT)} -> {remote}/")

    if args.dry_run:
        return 0

    api = HfApi(token=token)
    create_repo(repo_id, repo_type="dataset", private=private, exist_ok=True)
    print(f"\nCreated/verified dataset: https://huggingface.co/datasets/{repo_id}")

    readme_path = PROJECT_ROOT / "data" / "hf_dataset_README.md"
    readme_path.write_text(DEFAULT_README.replace("REPO_ID", repo_id), encoding="utf-8")
    api.upload_file(
        path_or_fileobj=str(readme_path),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset",
        commit_message="Add dataset README",
    )

    for local, path_in_repo in uploads:
        print(f"\nUploading {local.name} -> {path_in_repo} ...")
        if local.is_file():
            api.upload_file(
                path_or_fileobj=str(local),
                path_in_repo=path_in_repo,
                repo_id=repo_id,
                repo_type="dataset",
                commit_message=f"Upload {path_in_repo}",
            )
        else:
            api.upload_folder(
                folder_path=str(local),
                path_in_repo=path_in_repo,
                repo_id=repo_id,
                repo_type="dataset",
                commit_message=f"Upload {path_in_repo}",
            )

    print(f"\nDone. Dataset: https://huggingface.co/datasets/{repo_id}")
    print("Set HF_DATASET_REPO in .env for future uploads.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
