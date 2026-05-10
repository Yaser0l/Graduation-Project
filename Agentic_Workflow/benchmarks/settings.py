"""Benchmark configuration knobs.

Everything here is overridable via environment variables so the same code can
run unchanged in CI, in a local laptop, or in a managed eval pipeline.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

# Disable ragas phone-home telemetry by default. Users can opt in by setting
# RAGAS_DO_NOT_TRACK=false before launching the benchmark.
os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")

import config as app_config  # noqa: E402  -- needs the env var set first

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET_PATH = ROOT_DIR / "datasets" / "automotive_seed.jsonl"
DEFAULT_REPORT_DIR = ROOT_DIR / "reports"
DEFAULT_CACHE_DIR = ROOT_DIR / ".ragas_cache"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# -----------------------------------------------------------------------------
# Default thresholds. A metric falling below its threshold marks the run as
# failing (non-zero exit code) so the benchmark can gate CI.
# -----------------------------------------------------------------------------
DEFAULT_THRESHOLDS: Dict[str, float] = {
    "faithfulness": 0.70,
    "answer_relevancy": 0.70,
    "context_precision_with_reference": 0.60,
    "context_recall": 0.60,
    "answer_correctness": 0.60,
    "semantic_similarity": 0.70,
    # offline retrieval-only metrics computed without an LLM
    "retrieval_hit_rate": 0.80,
    "retrieval_mrr": 0.50,
}


@dataclass(frozen=True)
class BenchmarkSettings:
    """Frozen settings snapshot used by the runner."""

    judge_model: str = field(default_factory=lambda: os.getenv("BENCHMARK_JUDGE_MODEL", app_config.LLM_MODEL))
    judge_provider: str = field(default_factory=lambda: os.getenv("BENCHMARK_JUDGE_PROVIDER", "openai"))
    judge_temperature: float = field(default_factory=lambda: _env_float("BENCHMARK_JUDGE_TEMPERATURE", 0.0))

    embedding_model: str = field(default_factory=lambda: os.getenv("BENCHMARK_EMBEDDING_MODEL", "all-MiniLM-L6-v2"))

    api_key: str = field(default_factory=lambda: app_config.OPENAI_API_KEY or "")
    base_url: str = field(default_factory=lambda: app_config.base_url or "")

    top_k: int = field(default_factory=lambda: _env_int("BENCHMARK_TOP_K", app_config.RAG_TOP_K))
    max_cases: int = field(default_factory=lambda: _env_int("BENCHMARK_MAX_CASES", 0))

    request_timeout_sec: int = field(default_factory=lambda: _env_int("BENCHMARK_TIMEOUT_SEC", 120))
    max_retries: int = field(default_factory=lambda: _env_int("BENCHMARK_MAX_RETRIES", 2))
    max_workers: int = field(default_factory=lambda: _env_int("BENCHMARK_MAX_WORKERS", 4))
    seed: int = field(default_factory=lambda: _env_int("BENCHMARK_SEED", 42))

    enable_cache: bool = field(default_factory=lambda: _env_bool("BENCHMARK_CACHE", True))
    cache_dir: Path = field(default_factory=lambda: Path(os.getenv("BENCHMARK_CACHE_DIR", str(DEFAULT_CACHE_DIR))))

    dataset_path: Path = field(default_factory=lambda: Path(os.getenv("BENCHMARK_DATASET", str(DEFAULT_DATASET_PATH))))
    report_dir: Path = field(default_factory=lambda: Path(os.getenv("BENCHMARK_REPORT_DIR", str(DEFAULT_REPORT_DIR))))

    thresholds: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_THRESHOLDS))

    def validate(self) -> None:
        """Fail fast with a readable message when required config is missing."""
        if not self.api_key:
            raise RuntimeError(
                "LLM API key is empty — set OPENAI_API_KEY/BIGMODEL_API_KEY in .env "
                "before running the benchmark (or run with --mode lite)."
            )
        if not self.base_url:
            raise RuntimeError(
                "BASE_URL is empty — set BASE_URL in .env to the OpenAI-compatible "
                "endpoint (e.g. https://open.bigmodel.cn/api/paas/v4)."
            )


def load_settings() -> BenchmarkSettings:
    """Build a fresh settings snapshot from the current environment."""
    return BenchmarkSettings()
