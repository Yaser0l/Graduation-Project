---
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
huggingface-cli download aziz9788/automotive-rag-kb --repo-type dataset --local-dir ./data --token $HF_TOKEN
```

Then point `CHROMA_DB_PATH=./data/chroma_db` and `RAG_SOURCES_DIR=./data/sources`.
