"""RAGAS-driven evaluation entry point.

Two modes:

* ``full``  — run the configured LLM (default GLM-5.1) against the production
  RAG pipeline, then evaluate with RAGAS faithfulness / answer relevancy /
  context precision / context recall / answer correctness / semantic similarity.
* ``lite``  — only run retrieval + offline metrics (hit-rate, MRR, semantic
  similarity against the ground truth). Useful for fast PR-level smoke runs
  that should not call any LLM.
"""
from __future__ import annotations

import logging
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence

# Ragas honours this env var on import.
os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")

import nest_asyncio  # noqa: E402  ragas runs an inner event loop
from openai import OpenAI  # noqa: E402

from .dataset import TestCase  # noqa: E402
from .settings import BenchmarkSettings  # noqa: E402

# Defer pipeline imports — they pull in Chroma + sentence-transformers and
# we don't want unit tests of the offline helpers to drag those in.
if False:  # pragma: no cover - typing only
    from .pipeline import RagAnswer, RagPipeline  # noqa: F401

logger = logging.getLogger(__name__)
nest_asyncio.apply()

LLM_METRIC_NAMES = (
    "faithfulness",
    "answer_relevancy",
    "context_precision_with_reference",
    "context_recall",
    "answer_correctness",
    "semantic_similarity",
)
RETRIEVAL_METRIC_NAMES = ("retrieval_hit_rate", "retrieval_mrr")


@dataclass
class CaseResult:
    """Per-case output captured before/after RAGAS scoring."""

    case_id: str
    question: str
    ground_truth: str
    response: str
    retrieved_contexts: List[str]
    retrieval_scores: List[float]
    tags: List[str] = field(default_factory=list)
    latency_sec: float = 0.0
    error: Optional[str] = None
    metrics: Dict[str, Optional[float]] = field(default_factory=dict)


@dataclass
class BenchmarkReport:
    """Top-level report aggregating per-case results and pass/fail status."""

    mode: str
    judge_model: str
    embedding_model: str
    base_url: str
    case_count: int
    cases: List[CaseResult]
    aggregate: Dict[str, float]
    thresholds: Dict[str, float]
    failures: Dict[str, float]
    started_at: float
    finished_at: float

    @property
    def passed(self) -> bool:
        return not self.failures

    @property
    def duration_sec(self) -> float:
        return max(0.0, self.finished_at - self.started_at)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "judge_model": self.judge_model,
            "embedding_model": self.embedding_model,
            "base_url": self.base_url,
            "case_count": self.case_count,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_sec": self.duration_sec,
            "passed": self.passed,
            "thresholds": self.thresholds,
            "failures": self.failures,
            "aggregate": self.aggregate,
            "cases": [asdict(c) for c in self.cases],
        }


# -----------------------------------------------------------------------------
# Pipeline execution (same in both modes)
# -----------------------------------------------------------------------------

def _run_single(case: TestCase, pipeline, retrieval_only: bool) -> CaseResult:
    from .pipeline import RagAnswer  # local import keeps unit tests light
    start = time.perf_counter()
    error: Optional[str] = None
    try:
        answer = pipeline.retrieve(case.question) if retrieval_only else pipeline.answer(case.question)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failed for case %s", case.id)
        error = f"{type(exc).__name__}: {exc}"
        answer = RagAnswer(question=case.question, response="", retrieved_contexts=[], retrieval_scores=[])

    latency = time.perf_counter() - start
    return CaseResult(
        case_id=case.id,
        question=case.question,
        ground_truth=case.ground_truth,
        response=answer.response,
        retrieved_contexts=list(answer.retrieved_contexts),
        retrieval_scores=[float(s) for s in answer.retrieval_scores],
        tags=list(case.tags),
        latency_sec=latency,
        error=error,
    )


def _run_pipeline(
    cases: Sequence[TestCase],
    pipeline,
    settings: BenchmarkSettings,
    retrieval_only: bool,
) -> List[CaseResult]:
    workers = max(1, min(settings.max_workers, len(cases)))
    results: List[Optional[CaseResult]] = [None] * len(cases)
    if workers == 1:
        for idx, case in enumerate(cases):
            results[idx] = _run_single(case, pipeline, retrieval_only)
        return [r for r in results if r is not None]

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_idx = {pool.submit(_run_single, case, pipeline, retrieval_only): i for i, case in enumerate(cases)}
        for fut in as_completed(future_to_idx):
            idx = future_to_idx[fut]
            results[idx] = fut.result()
    return [r for r in results if r is not None]


# -----------------------------------------------------------------------------
# Offline retrieval metrics (no LLM required)
# -----------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _retrieval_signal(case: TestCase, contexts: Sequence[str]) -> Dict[str, Optional[float]]:
    """Cheap retrieval-only metrics computed without RAGAS:

    * ``retrieval_hit_rate`` — 1.0 if any retrieved chunk substring-overlaps the
      ground-truth answer (or any explicitly provided reference context).
    * ``retrieval_mrr``    — reciprocal rank of the first hit.
    """
    if not contexts:
        return {"retrieval_hit_rate": 0.0, "retrieval_mrr": 0.0}

    needles = [_normalize(case.ground_truth)] + [_normalize(rc) for rc in case.reference_contexts]
    needles = [n for n in needles if n]

    for rank, ctx in enumerate(contexts, start=1):
        haystack = _normalize(ctx)
        for needle in needles:
            # Use a fragment match so partial-overlap counts as a hit.
            sample_size = min(len(needle), 80)
            if sample_size == 0:
                continue
            fragment = needle[:sample_size]
            if fragment in haystack or haystack in needle:
                return {"retrieval_hit_rate": 1.0, "retrieval_mrr": 1.0 / rank}

    return {"retrieval_hit_rate": 0.0, "retrieval_mrr": 0.0}


# -----------------------------------------------------------------------------
# RAGAS scoring (full mode)
# -----------------------------------------------------------------------------

def _build_judge(settings: BenchmarkSettings):
    from ragas.llms import llm_factory

    cache = None
    if settings.enable_cache:
        try:
            from ragas.cache import DiskCacheBackend
            settings.cache_dir.mkdir(parents=True, exist_ok=True)
            cache = DiskCacheBackend(cache_dir=str(settings.cache_dir))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Disk cache disabled (%s)", exc)

    client_kwargs: Dict[str, Any] = {"api_key": settings.api_key}
    if settings.base_url:
        client_kwargs["base_url"] = settings.base_url
    if settings.request_timeout_sec:
        client_kwargs["timeout"] = settings.request_timeout_sec

    client = OpenAI(**client_kwargs)
    return llm_factory(
        model=settings.judge_model,
        provider=settings.judge_provider,
        client=client,
        cache=cache,
        temperature=settings.judge_temperature,
    )


def _build_embeddings(settings: BenchmarkSettings):
    from ragas.embeddings import HuggingfaceEmbeddings

    return HuggingfaceEmbeddings(model_name=settings.embedding_model)


def _build_metrics(judge, embeddings):
    from ragas.metrics.collections import (
        AnswerCorrectness,
        AnswerRelevancy,
        ContextPrecisionWithReference,
        ContextRecall,
        Faithfulness,
        SemanticSimilarity,
    )

    return [
        Faithfulness(llm=judge),
        AnswerRelevancy(llm=judge, embeddings=embeddings),
        ContextPrecisionWithReference(llm=judge),
        ContextRecall(llm=judge),
        AnswerCorrectness(llm=judge, embeddings=embeddings),
        SemanticSimilarity(embeddings=embeddings),
    ]


def _ragas_evaluate(
    case_results: Sequence[CaseResult],
    settings: BenchmarkSettings,
) -> Dict[str, Dict[str, Optional[float]]]:
    """Run RAGAS over the pipeline outputs and return per-case scores keyed by case id."""
    from ragas import EvaluationDataset, SingleTurnSample, evaluate
    from ragas.run_config import RunConfig

    eligible = [c for c in case_results if c.error is None and c.response and c.retrieved_contexts]
    skipped = [c for c in case_results if c not in eligible]
    for c in skipped:
        logger.warning(
            "Skipping RAGAS evaluation for case %s (error=%s, has_response=%s, ctx=%d)",
            c.case_id, c.error, bool(c.response), len(c.retrieved_contexts),
        )

    if not eligible:
        return {c.case_id: {} for c in case_results}

    samples = [
        SingleTurnSample(
            user_input=c.question,
            response=c.response,
            retrieved_contexts=c.retrieved_contexts,
            reference=c.ground_truth,
        )
        for c in eligible
    ]
    dataset = EvaluationDataset(samples=samples)

    judge = _build_judge(settings)
    embeddings = _build_embeddings(settings)
    metrics = _build_metrics(judge, embeddings)

    run_config = RunConfig(
        timeout=settings.request_timeout_sec,
        max_retries=settings.max_retries,
        max_workers=settings.max_workers,
        seed=settings.seed,
    )

    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        run_config=run_config,
        raise_exceptions=False,
        show_progress=True,
    )

    df = result.to_pandas()
    case_id_to_metrics: Dict[str, Dict[str, Optional[float]]] = {c.case_id: {} for c in case_results}
    for case, (_, row) in zip(eligible, df.iterrows()):
        scores: Dict[str, Optional[float]] = {}
        for name in LLM_METRIC_NAMES:
            value = row.get(name)
            scores[name] = None if value is None or (isinstance(value, float) and math.isnan(value)) else float(value)
        case_id_to_metrics[case.case_id] = scores
    return case_id_to_metrics


# -----------------------------------------------------------------------------
# Aggregation + threshold gating
# -----------------------------------------------------------------------------

def _aggregate(cases: Sequence[CaseResult]) -> Dict[str, float]:
    sums: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    for case in cases:
        for name, value in case.metrics.items():
            if value is None or (isinstance(value, float) and math.isnan(value)):
                continue
            sums[name] = sums.get(name, 0.0) + float(value)
            counts[name] = counts.get(name, 0) + 1
    return {name: sums[name] / counts[name] for name in sums}


def _check_thresholds(aggregate: Dict[str, float], thresholds: Dict[str, float]) -> Dict[str, float]:
    failures: Dict[str, float] = {}
    for name, minimum in thresholds.items():
        observed = aggregate.get(name)
        if observed is None:
            continue
        if observed < minimum:
            failures[name] = observed
    return failures


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def run_benchmark(
    cases: Sequence[TestCase],
    settings: BenchmarkSettings,
    mode: str = "full",
) -> BenchmarkReport:
    """Run the benchmark end-to-end and return a fully-populated report."""
    if mode not in {"full", "lite"}:
        raise ValueError(f"Unknown benchmark mode: {mode!r} (expected 'full' or 'lite')")
    if mode == "full":
        settings.validate()

    from .pipeline import RagPipeline  # deferred for lighter top-level imports
    pipeline = RagPipeline(settings)
    started_at = time.time()
    retrieval_only = mode == "lite"

    logger.info("Running %d cases (mode=%s, workers=%d, top_k=%d)", len(cases), mode, settings.max_workers, settings.top_k)
    case_results = _run_pipeline(cases, pipeline, settings, retrieval_only=retrieval_only)

    for case, result in zip(cases, case_results):
        result.metrics.update(_retrieval_signal(case, result.retrieved_contexts))

    if mode == "full":
        try:
            ragas_scores = _ragas_evaluate(case_results, settings)
            for result in case_results:
                result.metrics.update(ragas_scores.get(result.case_id, {}))
        except Exception as exc:  # noqa: BLE001
            logger.exception("RAGAS evaluation failed; reporting retrieval-only metrics")
            for result in case_results:
                result.error = result.error or f"ragas: {type(exc).__name__}: {exc}"

    finished_at = time.time()
    aggregate = _aggregate(case_results)
    failures = _check_thresholds(aggregate, settings.thresholds)

    return BenchmarkReport(
        mode=mode,
        judge_model=settings.judge_model,
        embedding_model=settings.embedding_model,
        base_url=settings.base_url,
        case_count=len(case_results),
        cases=case_results,
        aggregate=aggregate,
        thresholds=dict(settings.thresholds),
        failures=failures,
        started_at=started_at,
        finished_at=finished_at,
    )
