"""JSONL dataset loader for benchmark test cases."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class TestCase:
    """A single benchmark example."""

    id: str
    question: str
    ground_truth: str
    reference_contexts: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict) -> "TestCase":
        missing = [f for f in ("id", "question", "ground_truth") if not payload.get(f)]
        if missing:
            raise ValueError(f"Test case missing required fields: {missing} (payload: {payload!r})")
        return cls(
            id=str(payload["id"]),
            question=str(payload["question"]).strip(),
            ground_truth=str(payload["ground_truth"]).strip(),
            reference_contexts=[str(c).strip() for c in payload.get("reference_contexts", []) if str(c).strip()],
            tags=[str(t) for t in payload.get("tags", [])],
        )


def load_dataset(path: Path) -> List[TestCase]:
    """Load a JSONL benchmark dataset, skipping blank lines."""
    if not path.exists():
        raise FileNotFoundError(f"Benchmark dataset not found: {path}")

    cases: List[TestCase] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_num, raw in enumerate(fh, start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_num} is not valid JSON ({exc})") from exc
            cases.append(TestCase.from_dict(payload))

    if not cases:
        raise ValueError(f"Benchmark dataset is empty: {path}")

    seen_ids = set()
    for case in cases:
        if case.id in seen_ids:
            raise ValueError(f"Duplicate test case id: {case.id}")
        seen_ids.add(case.id)

    return cases


def sample(cases: Iterable[TestCase], max_cases: int, seed: Optional[int] = None) -> List[TestCase]:
    """Optionally cap the dataset for fast smoke runs (deterministic given seed)."""
    cases_list = list(cases)
    if max_cases <= 0 or max_cases >= len(cases_list):
        return cases_list
    rng = random.Random(seed)
    return rng.sample(cases_list, max_cases)
