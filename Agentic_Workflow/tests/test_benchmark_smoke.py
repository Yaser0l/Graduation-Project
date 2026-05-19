"""Smoke tests for the benchmark suite — no LLM calls, no network."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")


def test_dataset_loads_and_is_unique():
    from benchmarks.dataset import load_dataset
    from benchmarks.settings import DEFAULT_DATASET_PATH

    cases = load_dataset(DEFAULT_DATASET_PATH)
    assert len(cases) >= 5, "Seed dataset should have at least a handful of cases"
    assert len({c.id for c in cases}) == len(cases), "case ids must be unique"
    for case in cases:
        assert case.question
        assert case.ground_truth


def test_settings_defaults_load():
    from benchmarks.settings import load_settings

    settings = load_settings()
    assert settings.judge_model
    assert settings.embedding_model
    assert settings.thresholds
    assert settings.top_k >= 1


def test_retrieval_signal_handles_empty_contexts():
    from benchmarks.dataset import TestCase
    from benchmarks.ragas_runner import _retrieval_signal

    case = TestCase(id="t", question="q?", ground_truth="something specific")
    out = _retrieval_signal(case, [])
    assert out == {"retrieval_hit_rate": 0.0, "retrieval_mrr": 0.0}


def test_retrieval_signal_detects_substring_hit():
    from benchmarks.dataset import TestCase
    from benchmarks.ragas_runner import _retrieval_signal

    case = TestCase(id="t", question="q?", ground_truth="The catalytic converter is below threshold")
    out = _retrieval_signal(case, ["junk text", "the catalytic converter is below threshold"])
    assert out["retrieval_hit_rate"] == 1.0
    assert out["retrieval_mrr"] == pytest.approx(0.5)
