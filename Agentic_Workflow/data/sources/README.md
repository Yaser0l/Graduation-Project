# RAG source data and ingestion

This directory holds downloaded OBD-II / DTC databases and OEM owner manuals before they are indexed into Chroma (`data/chroma_db/`).

## One-command ingestion

```bash
cd Agentic_Workflow
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest tests/ -q --ignore=tests/test_keys.py -m "not live"
python scripts/ingest_rag_full.py --reset
```

### Flags

| Flag | Description |
|------|-------------|
| `--reset` | Wipe Chroma before indexing |
| `--skip-download` | Index files already under `data/sources/` |
| `--download-only` | Fetch sources only |
| `--force` | Re-download existing files |
| `--brands Toyota,Honda` | Limit makes |
| `--max-dtc 500` | Cap DTC rows (dev) |
| `--fixtures-dir tests/fixtures` | Use committed test fixtures (no HTTP) |

## Layout

```
data/sources/
  brand_sources.yaml   # vehicle seeds + adapter names
  manifest.json        # written after each run (gitignored)
  dtc/
    dtc_codes.db       # Wal33D SQLite (primary DTC source)
    dtc_list.pdf       # optional generic OBD-II list PDF (supplemental)
  manuals/{make}/{model}/{year}/owner_manual.pdf
```

See **[INGEST_BEST_PRACTICES.md](INGEST_BEST_PRACTICES.md)** for the production ingest policy (atomic DTC, manual overlap, dedupe).

## Data sources

- **DTC:** [Wal33D/dtc-database](https://github.com/Wal33D/dtc-database) (MIT), fallback [fabiovila/OBDIICodes](https://github.com/fabiovila/OBDIICodes)
- **Manuals:** Official OEM PDF URLs in `src/rag/sources/official_registry.py` (Honda techinfo, Ford fordservicecontent, GM contentdelivery, Nissan/Kia/Hyundai/Mercedes owner portals). Downloaded to `manuals/{make}/{model}/{year}/owner_manual.pdf` (gitignored — files exist on disk after ingest).

**Note:** `manuals/**` is in `.gitignore`, so the IDE may show an empty folder until you run download; use `manifest.json` for status.

## Success criteria (pytest gate)

| ID | Criterion |
|----|-----------|
| SC-01 | `pytest tests/ -m "not live"` exits 0 |
| SC-10 | Fixture ingest indexes ≥15 chunks |
| SC-12 | Retrieval finds P0420 |
| SC-13 | Retrieval finds manual tire-pressure content |
| SC-15 | `ingest_rag_full.py --help` exits 0 |

Full table: project plan *RAG ingestion (TDD)*.

## Python version

Use **Python 3.11 or 3.12**. Python 3.13 on Windows may crash when loading `sentence-transformers`. The ingest preflight step checks this before download/index.

## Copyright

Do not commit full OEM PDFs. Only official downloads or your own licensed copies. Attribution is recorded in `manifest.json`.
