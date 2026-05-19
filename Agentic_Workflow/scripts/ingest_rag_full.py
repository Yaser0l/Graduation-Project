#!/usr/bin/env python3
"""Single entry point: download DTC + manuals, index into Chroma, write manifest.

Usage:
    python scripts/ingest_rag_full.py --reset
    python scripts/ingest_rag_full.py --fixtures-dir tests/fixtures --skip-download --reset
"""
from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.ingest.preflight import EXIT_PREFLIGHT_FAIL, run_preflight
from src.rag.ingest.runner import run_full_ingest
import config


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Full RAG ingestion: DTC + manuals into Chroma")
    parser.add_argument("--reset", action="store_true", help="Wipe Chroma collection before indexing")
    parser.add_argument("--skip-download", action="store_true", help="Index existing data/sources only")
    parser.add_argument("--download-only", action="store_true", help="Download sources without indexing")
    parser.add_argument("--force", action="store_true", help="Re-download even if files exist")
    parser.add_argument("--brands", default="", help="Comma-separated make filter (e.g. Toyota,Honda)")
    parser.add_argument("--max-dtc", type=int, default=0, help="Cap DTC rows (0 = no cap)")
    parser.add_argument("--fixtures-dir", type=Path, default=None, help="Use test fixtures (implies copy, not HTTP)")
    parser.add_argument("--sources-dir", type=Path, default=None, help="Override RAG_SOURCES_DIR")
    parser.add_argument("--chroma-dir", type=Path, default=None, help="Override CHROMA_DB_PATH")
    parser.add_argument("--quiet", action="store_true", help="Reduce log verbosity")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip environment checks (tests only)")
    parser.add_argument(
        "--fake-embeddings",
        action="store_true",
        help="Use deterministic embeddings (tests/CI; no sentence-transformers)",
    )
    parser.add_argument(
        "--import-dtc-pdf",
        type=Path,
        default=None,
        help="Copy a local generic DTC-list PDF into data/sources/dtc/dtc_list.pdf before ingest",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.fake_embeddings:
        import os

        os.environ["RAG_USE_FAKE_EMBEDDINGS"] = "1"
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    sources_dir = Path(args.sources_dir or config.RAG_SOURCES_DIR)
    if not sources_dir.is_absolute():
        sources_dir = PROJECT_ROOT / sources_dir
    chroma_dir = args.chroma_dir or config.CHROMA_DB_PATH
    if not Path(chroma_dir).is_absolute():
        chroma_dir = str(PROJECT_ROOT / chroma_dir)
    brand_config = sources_dir / "brand_sources.yaml"
    if not brand_config.exists():
        brand_config = PROJECT_ROOT / "data" / "sources" / "brand_sources.yaml"

    fixtures_dir = args.fixtures_dir
    if fixtures_dir and not fixtures_dir.is_absolute():
        fixtures_dir = PROJECT_ROOT / fixtures_dir

    brands = [b.strip() for b in args.brands.split(",") if b.strip()] or None

    if args.import_dtc_pdf:
        src = args.import_dtc_pdf.expanduser().resolve()
        if not src.is_file():
            print(f"ERROR: --import-dtc-pdf not found: {src}", file=sys.stderr)
            return 1
        dest = sources_dir / "dtc" / "dtc_list.pdf"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print(f"Imported DTC list PDF -> {dest}")

    if not args.skip_preflight:
        pre = run_preflight(PROJECT_ROOT, sources_dir, Path(chroma_dir))
        for msg in pre.messages:
            print(msg)
        if not pre.ok:
            return EXIT_PREFLIGHT_FAIL

    try:
        result = run_full_ingest(
            PROJECT_ROOT,
            sources_dir,
            chroma_dir,
            brand_config,
            reset=args.reset,
            skip_download=args.skip_download,
            download_only=args.download_only,
            force=args.force,
            brands=brands,
            max_dtc=args.max_dtc,
            fixtures_dir=fixtures_dir,
            skip_preflight=True,
        )
    except Exception as exc:
        logging.error("Ingest failed: %s", exc)
        return 1

    sources = result.get("sources", [])
    _print_download_summary(sources)

    if result.get("phase") == "download":
        manual_ok = sum(1 for s in sources if s.get("kind") == "manual" and s.get("status") == "ok")
        if manual_ok == 0 and any(s.get("kind") == "manual" for s in sources):
            print("ERROR: No manuals downloaded. See manifest.json.", file=sys.stderr)
            return 1
        return 0

    stats = result.get("stats", {})
    print("Ingest complete.")
    print(f"  Chunks indexed: {stats.get('chunks_indexed', stats.get('total_chunks', 0))}")
    print(f"  DTC chunks: {stats.get('dtc', 0)}")
    print(f"  Manual chunks: {stats.get('manual', 0)}")
    if stats.get("chunks_indexed", 0) == 0 and stats.get("total_chunks", 0) == 0:
        print("ERROR: No chunks indexed.", file=sys.stderr)
        return 1
    if stats.get("manual", 0) == 0 and any(s.get("kind") == "manual" for s in sources):
        print("WARNING: DTC indexed but no manual chunks (check manual downloads in manifest).", file=sys.stderr)
    return 0


def _print_download_summary(sources: list) -> None:
    dtc = [s for s in sources if s.get("kind") == "dtc"]
    manuals = [s for s in sources if s.get("kind") == "manual"]
    if dtc:
        print(f"DTC: {dtc[0].get('status', '?')} -> {dtc[0].get('path', '')}")
    if manuals:
        ok = sum(1 for m in manuals if m.get("status") == "ok")
        print(f"Manuals: {ok}/{len(manuals)} downloaded to data/sources/manuals/")
        for m in manuals:
            if m.get("status") != "ok":
                print(f"  FAIL {m.get('make')} {m.get('model')} {m.get('year')}: {m.get('error', '')[:120]}")


if __name__ == "__main__":
    raise SystemExit(main())
