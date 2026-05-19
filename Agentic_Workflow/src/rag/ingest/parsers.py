"""Parse DTC databases and owner-manual PDFs into LangChain Documents."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from langchain_core.documents import Document

DTC_REQUIRED_META = ("type", "code", "make")

# OBD-II generic list PDF lines: "P0100 Mass or Volume Air Flow Circuit Malfunction"
_DTC_LINE_RE = re.compile(
    r"^([PCBU][0-9A-F]{4})\s+(.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def _normalize_code(code: str) -> str:
    raw = re.sub(r"\s+", "", (code or "").strip().upper())
    return raw.split("/")[0] if raw else raw


def _infer_system(code: str, row: Dict[str, Any]) -> str:
    if row.get("system"):
        return str(row["system"]).lower()
    prefix = _normalize_code(code)[:1] if code else ""
    if prefix == "P":
        return "powertrain"
    if prefix == "C":
        return "chassis"
    if prefix == "B":
        return "body"
    if prefix == "U":
        return "network"
    return "unknown"


def dtc_row_to_document(row: Dict[str, Any], source: str = "dtc-database") -> Document:
    """Convert a single DTC JSON row to a Document with required metadata."""
    code = _normalize_code(str(row.get("code") or row.get("Code") or row.get("DTC") or ""))
    if not code:
        raise ValueError(f"DTC row missing code: {row!r}")

    description = (
        row.get("description")
        or row.get("Description")
        or row.get("definition")
        or row.get("text")
        or ""
    )
    causes = row.get("causes") or row.get("Causes") or row.get("possible_causes") or ""
    make = str(row.get("make") or row.get("Make") or row.get("manufacturer") or "generic")
    system = _infer_system(code, row)

    parts = [f"{code} ({make}): {description}".strip()]
    if causes:
        parts.append(f"Common causes: {causes}")
    page_content = ". ".join(p for p in parts if p)

    metadata = {
        "type": "dtc",
        "code": code,
        "make": make,
        "system": system,
        "source": source,
        "lang": "en",
    }
    return Document(page_content=page_content, metadata=metadata)


def load_dtc_json(path: Path, max_rows: int = 0, brands: Optional[Iterable[str]] = None) -> List[Document]:
    """Load DTC records from a JSON file (list or {codes: [...]} shape)."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        rows = raw.get("codes") or raw.get("data") or raw.get("dtc") or list(raw.values())
        if isinstance(rows, dict):
            rows = list(rows.values())
    else:
        rows = raw

    brand_set = {b.strip().lower() for b in brands} if brands else None
    docs: List[Document] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        make = str(row.get("make") or row.get("Make") or "generic").lower()
        if brand_set and make not in brand_set and make != "generic":
            continue
        docs.append(dtc_row_to_document(row, source=f"file:{path.name}"))
        if max_rows and len(docs) >= max_rows:
            break
    return docs


def load_dtc_sqlite(path: Path, max_rows: int = 0, brands: Optional[Iterable[str]] = None) -> List[Document]:
    """Load DTC rows from Wal33D dtc_codes.db (dtc_definitions table)."""
    brand_set = {b.strip().lower() for b in brands} if brands else None
    docs: List[Document] = []
    con = sqlite3.connect(path)
    try:
        cur = con.execute(
            "SELECT code, manufacturer, description, type FROM dtc_definitions WHERE locale = 'en'"
        )
        for code, manufacturer, description, _dtype in cur:
            row = {
                "code": code,
                "make": manufacturer or "generic",
                "description": description or "",
            }
            make = str(row["make"]).lower()
            if brand_set and make not in brand_set and make != "generic":
                continue
            docs.append(dtc_row_to_document(row, source=f"sqlite:{path.name}"))
            if max_rows and len(docs) >= max_rows:
                break
    finally:
        con.close()
    return docs


def load_dtc_source(path: Path, max_rows: int = 0, brands: Optional[Iterable[str]] = None) -> List[Document]:
    """Load DTC documents from JSON, SQLite, or a generic DTC-list PDF."""
    suffix = path.suffix.lower()
    if suffix == ".db":
        return load_dtc_sqlite(path, max_rows=max_rows, brands=brands)
    if suffix == ".pdf":
        return load_dtc_pdf(path, max_rows=max_rows)
    return load_dtc_json(path, max_rows=max_rows, brands=brands)


def load_dtc_pdf(path: Path, max_rows: int = 0) -> List[Document]:
    """Parse a generic OBD-II trouble-code list PDF (one Document per code)."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    docs: List[Document] = []
    seen: set[str] = set()
    for match in _DTC_LINE_RE.finditer(text):
        code = _normalize_code(match.group(1))
        description = match.group(2).strip()
        if not code or code in seen:
            continue
        seen.add(code)
        row = {"code": code, "description": description, "make": "generic"}
        docs.append(dtc_row_to_document(row, source=f"pdf:{path.name}"))
        if max_rows and len(docs) >= max_rows:
            break
    return docs


def load_dtc_directory(
    dtc_dir: Path,
    max_rows: int = 0,
    brands: Optional[Iterable[str]] = None,
) -> List[Document]:
    """Load all DTC sources under dtc_dir; dedupe by code (SQLite/JSON first, then PDFs)."""
    if not dtc_dir.exists():
        return []

    by_code: Dict[str, Document] = {}
    remaining = max_rows if max_rows else 0

    def _add_batch(batch: List[Document]) -> None:
        nonlocal remaining
        for doc in batch:
            code = _normalize_code(str(doc.metadata.get("code") or ""))
            if not code or code in by_code:
                continue
            by_code[code] = doc
            if remaining and len(by_code) >= remaining:
                return

    # Priority: primary Wal33D DB, then JSON, then supplemental PDFs
    db_path = dtc_dir / "dtc_codes.db"
    if db_path.exists():
        _add_batch(load_dtc_sqlite(db_path, max_rows=0, brands=brands))
    else:
        for db in sorted(dtc_dir.glob("*.db")):
            _add_batch(load_dtc_sqlite(db, max_rows=0, brands=brands))
            break

    if remaining and len(by_code) >= remaining:
        return list(by_code.values())[:remaining]

    for json_path in sorted(dtc_dir.glob("*.json")):
        _add_batch(load_dtc_json(json_path, max_rows=0, brands=brands))
        if remaining and len(by_code) >= remaining:
            return list(by_code.values())[:remaining]

    for pdf_path in sorted(dtc_dir.glob("*.pdf")):
        _add_batch(load_dtc_pdf(pdf_path, max_rows=0))
        if remaining and len(by_code) >= remaining:
            break

    out = list(by_code.values())
    return out[:remaining] if remaining else out


def parse_manual_pdf(
    path: Path,
    make: str = "unknown",
    model: str = "unknown",
    year: int = 0,
) -> List[Document]:
    """Extract text from a PDF owner manual, one Document per page with text."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    docs: List[Document] = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "type": "manual",
                    "make": make,
                    "model": model,
                    "year": year,
                    "page": page_num,
                    "source_file": path.name,
                    "source": "owner-manual",
                    "lang": "en",
                },
            )
        )
    return docs


def discover_manual_pdfs(manuals_root: Path) -> List[tuple[Path, str, str, int]]:
    """Walk manuals_root/{make}/{model}/{year}/*.pdf and return paths + metadata."""
    results: List[tuple[Path, str, str, int]] = []
    if not manuals_root.exists():
        return results
    for make_dir in manuals_root.iterdir():
        if not make_dir.is_dir():
            continue
        make = make_dir.name
        for model_dir in make_dir.iterdir():
            if not model_dir.is_dir():
                continue
            model = model_dir.name
            for year_dir in model_dir.iterdir():
                if not year_dir.is_dir():
                    continue
                try:
                    year = int(year_dir.name)
                except ValueError:
                    year = 0
                for pdf in year_dir.glob("*.pdf"):
                    results.append((pdf, make, model, year))
    return results


def load_all_sources(
    dtc_dir: Optional[Path],
    manuals_root: Optional[Path],
    max_dtc: int = 0,
    brands: Optional[Iterable[str]] = None,
) -> List[Document]:
    """Load DTC + manual documents from on-disk sources."""
    documents: List[Document] = []
    if dtc_dir and dtc_dir.is_dir():
        documents.extend(load_dtc_directory(dtc_dir, max_rows=max_dtc, brands=brands))
    elif dtc_dir and dtc_dir.is_file():
        documents.extend(load_dtc_source(dtc_dir, max_rows=max_dtc, brands=brands))
    if manuals_root and manuals_root.exists():
        for pdf_path, make, model, year in discover_manual_pdfs(manuals_root):
            documents.extend(parse_manual_pdf(pdf_path, make=make, model=model, year=year))
    return documents
