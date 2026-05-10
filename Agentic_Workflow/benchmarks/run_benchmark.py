"""CLI entry point: ``python -m benchmarks.run_benchmark``.

Examples
--------
Quick smoke run with no LLM (retrieval-only metrics)::

    python -m benchmarks.run_benchmark --mode lite --max-cases 5

Full run against GLM 5.1 (uses .env credentials)::

    python -m benchmarks.run_benchmark --mode full

The process exits with code 1 when any aggregate metric falls below its
configured threshold so the benchmark can gate CI.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Make `import config` and `import src.*` work when invoked via `python -m`.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Telemetry must be disabled before ragas is imported anywhere.
os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")

from benchmarks import settings as settings_module  # noqa: E402
from benchmarks.dataset import load_dataset, sample  # noqa: E402
from benchmarks.ragas_runner import run_benchmark  # noqa: E402
from benchmarks.reporting import write_reports  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="benchmarks", description="Run the RAGAS benchmark suite.")
    parser.add_argument(
        "--mode",
        choices=("full", "lite"),
        default=os.getenv("BENCHMARK_MODE", "full"),
        help="full = pipeline + RAGAS metrics (LLM judge); lite = retrieval-only (no LLM).",
    )
    parser.add_argument("--dataset", type=Path, default=None, help="Path to a JSONL benchmark dataset.")
    parser.add_argument("--report-dir", type=Path, default=None, help="Directory to write reports into.")
    parser.add_argument("--top-k", type=int, default=None, help="Override the retriever top-k.")
    parser.add_argument("--max-cases", type=int, default=None, help="Cap the number of cases for fast runs.")
    parser.add_argument("--judge-model", default=None, help="Override the judge model id (default: GLM 5.1).")
    parser.add_argument("--workers", type=int, default=None, help="Pipeline + RAGAS concurrency.")
    parser.add_argument("--no-cache", action="store_true", help="Disable RAGAS disk cache.")
    parser.add_argument("--quiet", action="store_true", help="Reduce log verbosity.")
    return parser.parse_args(argv)


def _apply_overrides(args: argparse.Namespace) -> settings_module.BenchmarkSettings:
    base = settings_module.load_settings()
    overrides: dict = {}
    if args.dataset is not None:
        overrides["dataset_path"] = args.dataset
    if args.report_dir is not None:
        overrides["report_dir"] = args.report_dir
    if args.top_k is not None:
        overrides["top_k"] = args.top_k
    if args.max_cases is not None:
        overrides["max_cases"] = args.max_cases
    if args.judge_model is not None:
        overrides["judge_model"] = args.judge_model
    if args.workers is not None:
        overrides["max_workers"] = args.workers
    if args.no_cache:
        overrides["enable_cache"] = False
    if not overrides:
        return base

    from dataclasses import replace
    return replace(base, **overrides)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )

    settings = _apply_overrides(args)
    settings.report_dir.mkdir(parents=True, exist_ok=True)

    cases = load_dataset(settings.dataset_path)
    cases = sample(cases, settings.max_cases, seed=settings.seed)
    if not cases:
        print("ERROR: no cases to evaluate (empty dataset).", file=sys.stderr)
        return 2

    report = run_benchmark(cases=cases, settings=settings, mode=args.mode)
    paths = list(write_reports(report, settings.report_dir))

    print()
    print(f"Mode: {report.mode}  judge={report.judge_model}  cases={report.case_count}  duration={report.duration_sec:.1f}s")
    for name, value in sorted(report.aggregate.items()):
        threshold = report.thresholds.get(name)
        marker = ""
        if threshold is not None:
            marker = "  PASS" if value >= threshold else "  FAIL"
        print(f"  {name:34s} {value:6.3f}{marker}")

    if report.failures:
        print()
        print("Failed thresholds:")
        for name, observed in report.failures.items():
            threshold = report.thresholds.get(name, 0.0)
            print(f"  - {name}: {observed:.3f} < {threshold:.2f}")

    print()
    print("Reports written:")
    for p in paths:
        print(f"  {p}")

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
