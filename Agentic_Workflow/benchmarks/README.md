# RAGAS Benchmark Suite

Production-style evaluation of the Agentic Workflow's RAG component
(`src/rag/knowledge_base.py` + the GLM 5.1 grounded-generation step).

It uses the production Chroma vector store, the production
`HuggingFaceEmbeddings("all-MiniLM-L6-v2")` retriever, and the configured chat
model (default `glm-5.1` via the BigModel OpenAI-compatible endpoint) and
scores the results with [RAGAS](https://github.com/explodinggradients/ragas).

## Layout

```
benchmarks/
├── datasets/automotive_seed.jsonl   # curated Q + ground-truth set
├── settings.py                      # env-driven configuration
├── pipeline.py                      # production-equivalent retrieve+generate
├── ragas_runner.py                  # RAGAS metrics + offline retrieval signal
├── reporting.py                     # JSON / CSV / Markdown writers
├── run_benchmark.py                 # CLI entry: `python -m benchmarks.run_benchmark`
└── reports/                         # timestamped output directories (gitignored)
```

## Quick start

```powershell
# from the repo root
cd Agentic_Workflow
.\.venv\Scripts\Activate.ps1

# Lite mode: retrieval-only, never calls the LLM (fast PR-level smoke test)
python -m benchmarks.run_benchmark --mode lite --max-cases 5

# Full mode: GLM 5.1 grounded answers + RAGAS LLM judge
python -m benchmarks.run_benchmark --mode full
```

Reports land in a timestamped folder under `benchmarks/reports/`:

* `report.json` — full machine-readable per-case + aggregate metrics
* `report.csv`  — per-case scores for spreadsheet/notebook analysis
* `report.md`   — human-readable summary with PASS/FAIL badges

The CLI returns exit code `1` whenever any aggregate metric falls below its
configured threshold, which makes it CI-gate-friendly.

## CLI flags

| Flag | Default | Description |
| --- | --- | --- |
| `--mode {full,lite}` | `full` | `lite` skips the judge LLM and only computes retrieval metrics. |
| `--dataset PATH` | `benchmarks/datasets/automotive_seed.jsonl` | Path to a JSONL test set. |
| `--report-dir PATH` | `benchmarks/reports/` | Parent directory for the timestamped output folder. |
| `--top-k N` | `config.RAG_TOP_K` | Override the retriever depth. |
| `--max-cases N` | `0` (no cap) | Run a deterministic random subset. |
| `--judge-model NAME` | `config.LLM_MODEL` (`glm-5.1`) | Override the judge model id. |
| `--workers N` | `4` | Concurrency for both the pipeline and RAGAS. |
| `--no-cache` | off | Disable the disk cache used for repeated RAGAS calls. |
| `--quiet` | off | Lower the log level to `WARNING`. |

Every flag also has an environment variable equivalent (see `settings.py`).

## Metrics

| Metric | Needs LLM | Needs reference | Default threshold |
| --- | --- | --- | --- |
| `faithfulness` | yes | no | 0.70 |
| `answer_relevancy` | yes | no | 0.70 |
| `context_precision_with_reference` | yes | yes | 0.60 |
| `context_recall` | yes | yes | 0.60 |
| `answer_correctness` | yes | yes | 0.60 |
| `semantic_similarity` | no | yes | 0.70 |
| `retrieval_hit_rate` | no | yes | 0.80 |
| `retrieval_mrr` | no | yes | 0.50 |

Override any threshold by editing `DEFAULT_THRESHOLDS` in `settings.py`, or
by passing custom values programmatically via `BenchmarkSettings(thresholds=...)`.

## Authoring test cases

Each line in `datasets/*.jsonl` is one example:

```json
{
  "id": "tc_p0420",
  "question": "What does P0420 mean?",
  "ground_truth": "P0420 indicates ... ",
  "reference_contexts": ["optional canonical chunk text"],
  "tags": ["dtc", "engine"]
}
```

* `id` must be unique within the file.
* `reference_contexts` is optional but boosts `context_recall` and the
  offline `retrieval_hit_rate` checks.
* `tags` are propagated to the report for slicing.

## Reproducibility

* `BENCHMARK_SEED` (default `42`) is used both for sampling and for the
  RAGAS `RunConfig`.
* `RAGAS_DO_NOT_TRACK=true` is set automatically — no telemetry leaves the
  machine unless you explicitly opt in.
* GLM 5.1 responses are cached on disk under `benchmarks/.ragas_cache/` so
  repeated runs are nearly free; delete the folder or pass `--no-cache` to
  force fresh calls.
