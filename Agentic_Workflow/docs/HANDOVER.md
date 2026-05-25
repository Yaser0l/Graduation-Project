# Agentic Workflow — Handover Guide

This document explains how to set up, run, and maintain the **Multi-Agent Mechanic Workflow** with the **current RAG stack** (BGE embeddings, hybrid BM25+dense retrieval, cross-encoder rerank, section-aware ingest). It also covers downloading pre-built data from **Hugging Face** and expected disk/GPU requirements.

**Audience:** Developers taking over the graduation project codebase.

---

## 1. What this system does

| Layer                    | Role                                                        |
| ------------------------ | ----------------------------------------------------------- |
| **Router / main graph**  | Validates OBD2 input, runs OBD2 then Writer orchestrations  |
| **OBD2 orchestration**   | Load memory → Writer (RAG + web) → Observer (review) → Save |
| **Writer orchestration** | Product search → Technical report → Formatter → Save        |
| **RAG knowledge base**   | Chroma + BGE embeddings + BM25 + reranker                   |
| **Ingest pipeline**      | Download DTC DB + OEM manuals → chunk → index               |

Default LLM: **GLM-5.1** via Zhipu BigModel (OpenAI-compatible API).  
Default sample input: `data/sample_obd2_data.json` (2020 Toyota Camry, codes C0561, C0750).

---

## 2. Architecture (current approach)

### 2.1 Ingest-time (index)

```
data/sources/dtc/          → Wal33D SQLite + optional PDF
data/sources/manuals/      → OEM PDFs per make/model/year
        ↓
parsers.py + manual_chunking.py
        ↓
Chroma (BGE 1024-dim vectors) + bm25_index.pkl
        ↓
data/chroma_db/
```

| Policy     | Implementation                                                                                                            |
| ---------- | ------------------------------------------------------------------------------------------------------------------------- |
| DTC        | **One chunk per code** (`type=dtc`, `chunk_id=dtc:{make}:{CODE}`)                                                         |
| Manuals    | **Section-aware** splits, then 1000 char / 200 overlap; `parent_id` for citations                                         |
| Embeddings | `BAAI/bge-m3` target; on **Windows**, auto-maps to **`BAAI/bge-large-en-v1.5`** (1024-dim, GPU via sentence-transformers) |
| BM25       | Built after ingest → `data/chroma_db/bm25_index.pkl`                                                                      |

Entry script: `scripts/ingest_rag_full.py`  
Policy doc: `data/sources/INGEST_BEST_PRACTICES.md`

### 2.2 Query-time (retrieval)

```
User query / OBD2 codes
        ↓
Exact DTC lookup (metadata filter on code)  ← when applicable
        ↓
Dense top-50 (Chroma) + BM25 top-50 → RRF fusion
        ↓
Cross-encoder rerank (BAAI/bge-reranker-v2-m3) → top 5
        ↓
LLM agents (OBD2 writer, etc.)
```

| Setting              | Default | Meaning                            |
| -------------------- | ------- | ---------------------------------- |
| `RAG_RETRIEVE_K`     | 50      | Candidates before rerank           |
| `RAG_TOP_K`          | 5       | Chunks passed to agents            |
| `RAG_HYBRID_ENABLED` | true    | BM25 + dense                       |
| `RAG_RERANK_ENABLED` | true    | Cross-encoder rerank               |
| `RAG_TRACE_VECTORS`  | true    | Log cosine + 8-dim vector previews |

Core modules:

- `src/rag/knowledge_base.py` — Chroma, hybrid, rerank, `retrieve_detailed()`
- `src/rag/bm25_index.py`, `src/rag/hybrid.py`, `src/rag/reranker.py`
- `src/rag/retrieval_trace.py` — scored hits for debugging
- `src/tools/rag_tool.py` — LangChain tools used by OBD2 writer

### 2.3 Agent workflow graph

```
initialize → obd2_orchestration → writer_orchestration → finalize
                  │                        │
                  ├ load_memory            ├ product_researcher (Tavily PDP URLs)
                  ├ writer (RAG+web)       ├ technical_writer
                  ├ observer               ├ formatter
                  └ save_analysis          └ save_report
```

Run: `python src/main.py` or `python scripts/run_workflow_trace.py` (saves trace to `output/`).

---

## 3. Data inventory and sizes

### 3.1 On-disk layout (after full ingest)

| Path                            | Approx. size   | Description                                            |
| ------------------------------- | -------------- | ------------------------------------------------------ |
| `data/chroma_db/`               | **~530 MB**    | Chroma SQLite + HNSW vectors                           |
| `data/chroma_db/bm25_index.pkl` | **~15 MB**     | Serialized BM25 corpus                                 |
| `data/chroma_db/chroma.sqlite3` | **~76 MB**     | Chroma metadata DB                                     |
| `data/sources/dtc/`             | **~5–50 MB**   | `dtc_codes.db` (Wal33D), optional `dtc_list.pdf`       |
| `data/sources/manuals/`         | **~80–130 MB** | OEM PDFs (9 brands in registry; not all URLs download) |
| `data/sources/manifest.json`    | small          | Per-run download/index audit                           |
| `data/users/`                   | small          | Per-user profile/history (runtime)                     |
| **Total `data/`**               | **~665 MB**    | Typical full local install                             |

### 3.2 Index statistics (last successful ingest)

| Metric                  | Value                  |
| ----------------------- | ---------------------- |
| **Total chunks**        | ~38,568                |
| **DTC chunks**          | ~12,128                |
| **Manual chunks**       | ~26,440                |
| **Embedding dimension** | 1024                   |
| **Collection name**     | `automotive_knowledge` |

Manual chunk count is higher than page count because of **section-aware sub-chunking**.

### 3.3 What is NOT in git

Root `.gitignore` excludes:

- `.env` (secrets)
- `Agentic_Workflow/data/chroma_db/`
- `Agentic_Workflow/data/sources/manuals/**`
- `Agentic_Workflow/data/sources/dtc/**`
- `Agentic_Workflow/data/sources/manifest.json`

Use **Hugging Face** or re-run ingest to obtain data on a new machine.

---

## 4. Hugging Face dataset (pre-built data)

### 4.1 Dataset location

| Field    | Value                                                      |
| -------- | ---------------------------------------------------------- |
| **Repo** | `aziz9788/automotive-rag-kb`                               |
| **Type** | Dataset (private)                                          |
| **URL**  | https://huggingface.co/datasets/aziz9788/automotive-rag-kb |

Uploaded contents:

```
chroma_db/              # Full vector store + bm25_index.pkl
sources/dtc/            # SQLite + PDFs
sources/manuals/        # OEM PDF tree
sources/manifest.json
sources/brand_sources.yaml
sources/README.md
sources/INGEST_BEST_PRACTICES.md
README.md               # Dataset card
```

Upload script: `scripts/upload_hf_dataset.py`  
Re-upload after re-ingest: `python scripts/upload_hf_dataset.py`

### 4.2 Download data to a new machine

**Prerequisites:** Hugging Face account with access to the private dataset, read token in `.env`.

1. Copy `.env.example` → `.env` and set:

```env
HF_TOKEN=hf_your_read_or_write_token
HF_DATASET_REPO=aziz9788/automotive-rag-kb
```

2. Install CLI / hub:

```bash
pip install huggingface_hub
```

3. Download entire dataset into `data/`:

```bash
cd Agentic_Workflow
huggingface-cli login   # or rely on HF_TOKEN in .env
huggingface-cli download aziz9788/automotive-rag-kb \
  --repo-type dataset \
  --local-dir ./data \
  --token $HF_TOKEN
```

**Windows PowerShell:**

```powershell
$env:HF_TOKEN = "hf_..."   # or load from .env
huggingface-cli download aziz9788/automotive-rag-kb --repo-type dataset --local-dir .\data
```

4. Verify paths (defaults in `config.py`):

```text
CHROMA_DB_PATH=./data/chroma_db
RAG_SOURCES_DIR=./data/sources
```

5. Quick sanity check:

```bash
python -c "from src.rag.knowledge_base import knowledge_base; print(knowledge_base.get_stats())"
```

Expected: `total_chunks` ~38k, `hybrid_enabled: True`.

**Download size:** ~650–700 MB (same order as local `data/`).

### 4.3 Grant access to another collaborator

1. Hugging Face → dataset **Settings** → **Collaborators** (add their HF username), **or**
2. Share a fine-grained token with read access to that repo only.

Do **not** commit `HF_TOKEN` to git.

---

## 5. Setup from scratch (without HF download)

### 5.1 Prerequisites

| Requirement  | Notes                                                                                                        |
| ------------ | ------------------------------------------------------------------------------------------------------------ |
| **Python**   | **3.10–3.12** recommended (`.venv310` used in development). Avoid 3.13 on Windows for sentence-transformers. |
| **GPU**      | NVIDIA GPU + CUDA for ingest/query (RTX 20xx+ tested). CPU works but slow.                                   |
| **API keys** | `OPENAI_API_KEY` (or BigModel), optional `TAVILY_API_KEY`, optional `HF_TOKEN`                               |
| **Disk**     | **≥2 GB** free for data + models cache                                                                       |
| **RAM**      | **≥16 GB** recommended for full ingest + reranker                                                            |

### 5.2 Create environment

```powershell
cd Agentic_Workflow
uv sync
```

Fallback (pip):

```powershell
pip install -r requirements.txt
```

### 5.3 GPU stack (one-time)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_gpu_torch.ps1
```

This installs:

- PyTorch with CUDA 12.4
- `sentence-transformers`
- Smoke test: BGE-large on GPU

For ONNX GPU (optional fastembed path): `uv pip install onnxruntime-gpu`

### 5.4 Environment file

```powershell
copy .env.example .env
# Edit .env — see section 7
```

### 5.5 Full ingest (download + index)

```powershell
# Full pipeline: preflight → download OEM/DTC → index → manifest
uv run python scripts/ingest_rag_full.py --reset

# Skip download if sources/ already populated (e.g. after HF download)
uv run python scripts/ingest_rag_full.py --reset --skip-download

# Import local DTC PDF
uv run python scripts/ingest_rag_full.py --import-dtc-pdf "C:\path\to\dtc_list.pdf" --reset --skip-download
```

**Time:** ~30–60 min first run (downloads + GPU embedding of ~38k chunks).  
**Must use `--reset`** after changing embedding model or chunking policy.

### 5.6 Run tests

```bash
uv run pytest tests/ -q --ignore=tests/test_keys.py -m "not live"
```

Tests use `RAG_USE_FAKE_EMBEDDINGS=1` (see `tests/conftest.py`) — no GPU required for CI.

### 5.7 Run the agent workflow

```powershell
$env:PYTHONIOENCODING = "utf-8"
uv run python src/main.py
```

With full trace + saved report:

```powershell
uv run python scripts/run_workflow_trace.py
# Output: output/workflow_trace_YYYYMMDD_HHMMSS.md
#         output/workflow_trace_YYYYMMDD_HHMMSS.log
#         output/diagnostic_report_user_001_YYYYMMDD_HHMMSS.txt
```

### 5.8 Benchmarks (retrieval quality gate)

```bash
# Lite mode — no LLM, checks hit-rate / MRR thresholds
uv run python -m benchmarks.run_benchmark --mode lite --max-cases 20
```

See `benchmarks/README.md`. CI workflow: `.github/workflows/rag-benchmark.yml`.

---

## 6. Key scripts and files

| Path                                   | Purpose                             |
| -------------------------------------- | ----------------------------------- |
| `scripts/ingest_rag_full.py`           | Single entry: ingest + index        |
| `scripts/install_gpu_torch.ps1`        | CUDA PyTorch + embedding smoke test |
| `scripts/upload_hf_dataset.py`         | Push `data/` to HF dataset          |
| `scripts/run_workflow_trace.py`        | Full workflow + RAG trace logs      |
| `src/main.py`                          | CLI entry for sample OBD2 run       |
| `src/graph/main_graph.py`              | LangGraph main workflow             |
| `src/rag/knowledge_base.py`            | Retrieval + indexing                |
| `src/tools/rag_tool.py`                | RAG tools for agents                |
| `src/tools/tavily_tool.py`             | Web + **product PDP** search        |
| `src/rag/sources/official_registry.py` | OEM manual URLs                     |
| `data/sources/brand_sources.yaml`      | Vehicles to download                |
| `config.py`                            | All `RAG_*` and agent settings      |
| `benchmarks/`                          | RAGAS + offline retrieval metrics   |

---

## 7. Environment variables reference

| Variable                  | Required | Default                      | Description                     |
| ------------------------- | -------- | ---------------------------- | ------------------------------- |
| `OPENAI_API_KEY`          | Yes\*    | —                            | LLM (or use `BIGMODEL_API_KEY`) |
| `BASE_URL`                | Yes\*    | BigModel URL                 | OpenAI-compatible endpoint      |
| `LLM_MODEL`               | No       | `glm-5.1`                    | Chat model id                   |
| `TAVILY_API_KEY`          | No       | —                            | Web + product search            |
| `HF_TOKEN`                | For HF   | —                            | Upload/download dataset         |
| `HF_DATASET_REPO`         | No       | `aziz9788/automotive-rag-kb` | Dataset id                      |
| `CHROMA_DB_PATH`          | No       | `./data/chroma_db`           | Vector store                    |
| `RAG_SOURCES_DIR`         | No       | `./data/sources`             | Raw sources                     |
| `RAG_EMBEDDING_MODEL`     | No       | `BAAI/bge-m3`                | Embedding model name            |
| `RAG_EMBEDDING_DEVICE`    | No       | `auto`                       | `cuda` / `cpu`                  |
| `RAG_EMBEDDING_BACKEND`   | No       | `auto`                       | `st`, `fastembed`, `flag`       |
| `RAG_RETRIEVE_K`          | No       | `50`                         | Hybrid candidate count          |
| `RAG_TOP_K`               | No       | `5`                          | Final chunks to LLM             |
| `RAG_HYBRID_ENABLED`      | No       | `true`                       | BM25 + dense                    |
| `RAG_RERANK_ENABLED`      | No       | `true`                       | Cross-encoder rerank            |
| `RAG_RERANK_MODEL`        | No       | `BAAI/bge-reranker-v2-m3`    | Reranker                        |
| `RAG_TRACE_VECTORS`       | No       | `true`                       | Log cosine + vector previews    |
| `RAG_USE_FAKE_EMBEDDINGS` | Tests    | —                            | Set `1` for pytest              |

\*Required for full agent run; not for ingest-with-fake-embeddings tests.

---

## 8. Observability (RAG traces)

When agents call `retrieve_with_reflection`, the console prints:

```text
============================================================
RAG RETRIEVAL TRACE
============================================================
Query: ...
Candidates: 50 | hybrid=True | rerank=True
--- Rank 1 | rerank | chunk_id=dtc:generic:C0561 ---
  scores: cosine=0.62 dense_dist=0.38 bm25=... rrf=... rerank=0.11 final=0.11
  query_vec[1024] preview: [...]
  doc_vec[1024] preview: [...]
  meta: type=dtc code=C0561 make=GENERIC
  text: C0561 (GENERIC): Vacuum Sensor A/B Correlation
```

Returned JSON fields: `hits`, `retrieval_trace` on the tool result.

**Interpretation:**

- **cosine_similarity** — dot product on L2-normalized BGE vectors (0–1, higher = better).
- **dense_distance** — Chroma distance; `cosine ≈ 1 - distance` in cosine space.
- **rerank_score** — cross-encoder relevance (can be low in logit scale; rank order matters).

---

## 9. Product search (current behavior)

`search_products` in `src/tools/tavily_tool.py`:

- Uses Tavily **advanced** search on parts domains (Amazon, RockAuto, Toyota parts, etc.).
- **Filters out** category/listing URLs (e.g. `walmart.com/c/...`).
- **Prefers** product detail pages (`/dp/`, `/p/`, part numbers).

Product researcher prints `Product URL:` and `page_type: product_detail` in logs.

---

## 10. Known limitations (honest handover notes)

| Issue                      | Detail                                        | Mitigation                                                       |
| -------------------------- | --------------------------------------------- | ---------------------------------------------------------------- |
| **Missing DTC codes**      | e.g. `C0750` may be absent in Wal33D DB       | Supplement DB; verify with `lookup_dtc_code()`                   |
| **Wrong-make manual hits** | Semantic query can rank other brands' manuals | Use `retrieve_for_codes` + exact DTC; filter by `make` in future |
| **BGE-M3 on Windows**      | FlagEmbedding may crash                       | Auto fallback to `bge-large-en-v1.5`                             |
| **First query slow**       | Loads embedder + reranker (~1–2 min)          | Warm up once before demo                                         |
| **OEM copyright**          | Manuals must stay **private** on HF           | Do not make dataset public without rights                        |
| **Reflection score low**   | Threshold 0.7 often triggers web fallback     | Expected when manual fragments rank high                         |

---

## 11. Troubleshooting

| Symptom                                  | Fix                                                                  |
| ---------------------------------------- | -------------------------------------------------------------------- |
| `CUDA not available`                     | Run `scripts/install_gpu_torch.ps1`; verify `nvidia-smi`             |
| `too many SQL variables` on BM25 rebuild | Fixed via paginated rebuild; update `knowledge_base.py` if reappears |
| `UnicodeEncodeError` on Windows          | Set `$env:PYTHONIOENCODING="utf-8"`                                  |
| Empty `manuals/` in IDE                  | Normal — gitignored; check disk or HF download                       |
| Chroma dimension mismatch                | `ingest_rag_full.py --reset` after embedding change                  |
| HF 401 / 403                             | Token expired or no dataset access; refresh `HF_TOKEN`               |
| pytest hangs on workflow                 | Default suite excludes `test_workflow.py` (live LLM)                 |

---

## 12. Recommended handover checklist

- [ ] Clone repo, create `.venv310`, `uv sync --frozen` (fallback: `pip install -r requirements.txt`)
- [ ] Copy `.env.example` → `.env` (LLM + Tavily + HF tokens)
- [ ] Download HF dataset **or** run `ingest_rag_full.py --reset`
- [ ] Run `uv run python -c "from src.rag.knowledge_base import knowledge_base; print(knowledge_base.get_stats())"`
- [ ] Run `uv run pytest tests/ -q --ignore=tests/test_keys.py -m "not live"`
- [ ] Run `uv run python scripts/run_workflow_trace.py` once; review `output/workflow_trace_*.md`
- [ ] Run `uv run python -m benchmarks.run_benchmark --mode lite`
- [ ] Read `data/sources/INGEST_BEST_PRACTICES.md` for ingest/query policy
- [ ] Confirm HF dataset access for team members (private collaborators)

---

## 13. Security reminders

1. **Never commit** `.env`, API keys, or HF write tokens.
2. **Rotate** any token that was shared in chat or logs.
3. Keep the Hugging Face dataset **private** unless you have redistribution rights for OEM PDFs.
4. Wal33D DTC data is MIT-licensed; OEM manuals are not.

---

## 14. Quick command reference

```powershell
# --- Data from Hugging Face ---
uv run huggingface-cli download aziz9788/automotive-rag-kb --repo-type dataset --local-dir .\data

# --- Full re-ingest (local) ---
uv run python scripts/ingest_rag_full.py --reset --skip-download

# --- Upload to Hugging Face ---
uv run python scripts/upload_hf_dataset.py

# --- Run workflow ---
uv run python scripts/run_workflow_trace.py

# --- Tests ---
uv run pytest tests/ -q --ignore=tests/test_keys.py -m "not live"

# --- Benchmark ---
uv run python -m benchmarks.run_benchmark --mode lite
```

---

_Last updated: May 2026 — matches hybrid RAG + HF dataset `aziz9788/automotive-rag-kb`._
