"""Reporting helpers — write JSON, CSV, and a human-readable Markdown report."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Tuple

from .ragas_runner import BenchmarkReport


METRIC_DESCRIPTIONS = {
    "faithfulness": "Answer is grounded in retrieved context (no hallucinations).",
    "answer_relevancy": "Answer addresses the question.",
    "context_precision_with_reference": "Useful retrieved chunks are ranked higher.",
    "context_recall": "Retrieval covered the information in the reference answer.",
    "answer_correctness": "Answer matches the reference (LLM + embedding judged).",
    "semantic_similarity": "Embedding similarity vs reference answer.",
    "retrieval_hit_rate": "Fraction of cases where retrieval surfaced the reference content.",
    "retrieval_mrr": "Mean reciprocal rank of the first hit in retrieval.",
}


def _timestamp_dir(base: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = base / stamp
    out.mkdir(parents=True, exist_ok=True)
    return out


def _all_metric_names(report: BenchmarkReport) -> List[str]:
    seen: List[str] = []
    for case in report.cases:
        for name in case.metrics.keys():
            if name not in seen:
                seen.append(name)
    return seen


def _format_metric(value: float | None, threshold: float | None) -> str:
    if value is None:
        return "n/a"
    formatted = f"{value:.3f}"
    if threshold is None:
        return formatted
    badge = "PASS" if value >= threshold else "FAIL"
    return f"{formatted}  ({badge} >= {threshold:.2f})"


def _write_json(report: BenchmarkReport, path: Path) -> None:
    path.write_text(json.dumps(report.to_dict(), indent=2, default=str), encoding="utf-8")


def _write_csv(report: BenchmarkReport, path: Path) -> None:
    metric_names = _all_metric_names(report)
    fieldnames = [
        "case_id",
        "tags",
        "latency_sec",
        "error",
        "question",
        "ground_truth",
        "response",
        *metric_names,
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for case in report.cases:
            row = {
                "case_id": case.case_id,
                "tags": ";".join(case.tags),
                "latency_sec": f"{case.latency_sec:.3f}",
                "error": case.error or "",
                "question": case.question,
                "ground_truth": case.ground_truth,
                "response": case.response,
            }
            for name in metric_names:
                value = case.metrics.get(name)
                row[name] = "" if value is None else f"{value:.4f}"
            writer.writerow(row)


def _aggregate_table(report: BenchmarkReport) -> List[Tuple[str, str, str]]:
    rows = []
    for name in _all_metric_names(report):
        value = report.aggregate.get(name)
        threshold = report.thresholds.get(name)
        description = METRIC_DESCRIPTIONS.get(name, "")
        rows.append((name, _format_metric(value, threshold), description))
    return rows


def _write_markdown(report: BenchmarkReport, path: Path) -> None:
    lines: List[str] = []
    status = "PASS" if report.passed else "FAIL"
    lines.append(f"# RAGAS Benchmark Report — {status}")
    lines.append("")
    lines.append(f"- Mode: `{report.mode}`")
    lines.append(f"- Judge model: `{report.judge_model}`")
    lines.append(f"- Embedding model: `{report.embedding_model}`")
    lines.append(f"- Base URL: `{report.base_url or '(default)'}`")
    lines.append(f"- Cases: **{report.case_count}**")
    lines.append(f"- Duration: {report.duration_sec:.1f}s")
    lines.append("")

    lines.append("## Aggregate metrics")
    lines.append("")
    lines.append("| Metric | Score | Description |")
    lines.append("| --- | --- | --- |")
    for name, formatted, description in _aggregate_table(report):
        lines.append(f"| `{name}` | {formatted} | {description} |")
    lines.append("")

    if report.failures:
        lines.append("## Threshold failures")
        lines.append("")
        for name, observed in report.failures.items():
            threshold = report.thresholds.get(name)
            lines.append(f"- `{name}`: {observed:.3f} < {threshold:.2f}")
        lines.append("")

    lines.append("## Per-case results")
    lines.append("")
    metric_names = _all_metric_names(report)
    headers = ["case_id", "latency_sec", "error", *metric_names]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for case in report.cases:
        row = [
            case.case_id,
            f"{case.latency_sec:.2f}",
            (case.error or "").replace("|", r"\|"),
        ]
        for name in metric_names:
            value = case.metrics.get(name)
            row.append("n/a" if value is None else f"{value:.3f}")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_reports(report: BenchmarkReport, output_dir: Path) -> Iterable[Path]:
    """Write report.json + report.csv + report.md inside a timestamped subdir."""
    out_dir = _timestamp_dir(output_dir)
    json_path = out_dir / "report.json"
    csv_path = out_dir / "report.csv"
    md_path = out_dir / "report.md"
    _write_json(report, json_path)
    _write_csv(report, csv_path)
    _write_markdown(report, md_path)
    return [json_path, csv_path, md_path]
