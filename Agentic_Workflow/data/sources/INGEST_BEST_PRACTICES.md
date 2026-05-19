# RAG ingestion & retrieval best practices (production, May 2026)

## Ingest (index time)

| Practice | This repo | Rationale |
|----------|-----------|-----------|
| **Atomic DTC chunks** | One vector per OBD-II code + `chunk_id` | Exact code lookup |
| **Wal33D SQLite primary** | `dtc/dtc_codes.db` first | ~19k structured rows |
| **Supplemental DTC PDF** | `dtc/dtc_list.pdf` (deduped) | Fills gaps only |
| **Section-aware manuals** | `manual_chunking.py` | Splits on headings before char windows |
| **Parent document IDs** | `parent_id` per manual page | Citations back to make/model/year/page |
| **Manual char chunks** | 1000 / 200 overlap within sections | Narrative overlap without crossing sections blindly |
| **Official OEM PDFs** | `official_registry.py` | Publisher URLs only |
| **Embeddings** | BGE-large on GPU (Windows) / bge-m3 target | Strong dense retrieval |
| **BGE query/doc prefixes** | `sentence_transformer_embeddings.py` | Asymmetric search |
| **BM25 index persisted** | `data/chroma_db/bm25_index.pkl` | Lexical hybrid for codes & part numbers |
| **Batched index writes** | 500 chunks per Chroma batch | Large corpora |
| **Manifest + sha256** | `manifest.json` | Audit trail |

## Query time (production default)

| Practice | Config | Rationale |
|----------|--------|-----------|
| **Wide retrieve** | `RAG_RETRIEVE_K=50` | Recall before precision |
| **Hybrid fusion** | `RAG_HYBRID_ENABLED=true` | Dense + BM25 via RRF |
| **Cross-encoder rerank** | `RAG_RERANK_MODEL=BAAI/bge-reranker-v2-m3` | Largest quality lift |
| **Narrow return** | `RAG_TOP_K=5` | Final context for LLM |
| **Metadata filters** | `type`, `make`, `code` | `rag_tool.retrieve_for_codes` |

## Benchmarks / CI

```bash
# Retrieval-only gate (no LLM) — uses same KB as production
python -m benchmarks.run_benchmark --mode lite --max-cases 20

# Fails exit code 1 if retrieval_hit_rate < 0.80 or retrieval_mrr < 0.50
```

Set `BENCHMARK_TOP_K` / `BENCHMARK_RETRIEVE_K` to override; embedding model defaults to `RAG_EMBEDDING_MODEL`.

## Commands

```bash
# Full re-index after ingest/query stack changes (required)
python scripts/ingest_rag_full.py --reset --skip-download

# Standard production ingest
python scripts/ingest_rag_full.py --reset
```

## Sources layout

```
data/sources/dtc/
  dtc_codes.db
  dtc_list.pdf
data/sources/manuals/{Make}/{Model}/{Year}/owner_manual.pdf
data/chroma_db/
  bm25_index.pkl
```
