"""Section-aware manual chunking with parent document IDs for citations."""
from __future__ import annotations

import re
from typing import List, Tuple

from langchain_core.documents import Document

_HEADING_LINE = re.compile(
    r"^(?:"
    r"(?:CHAPTER|SECTION|PART)\s+[\dIVXLC]+"
    r"|\d+(?:\.\d+)*\s+[A-Z][A-Za-z0-9 \-/&]{2,}"
    r"|[A-Z][A-Z0-9 \-/&]{4,}$"
    r")",
    re.IGNORECASE,
)


def manual_parent_id(meta: dict) -> str:
    """Stable parent key for all chunks from one manual page."""
    make = meta.get("make") or "unknown"
    model = meta.get("model") or "unknown"
    year = meta.get("year") or 0
    page = meta.get("page") or 0
    source = meta.get("source_file") or "manual"
    return f"{make}|{model}|{year}|{source}|p{page}"


def _is_heading_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 120:
        return False
    if _HEADING_LINE.match(stripped):
        return True
    if stripped.isupper() and len(stripped.split()) <= 12:
        return True
    return False


def split_page_into_sections(text: str) -> List[Tuple[str, str]]:
    """Split page text into (section_title, body) pairs."""
    lines = (text or "").splitlines()
    sections: List[Tuple[str, str]] = []
    title = ""
    body_lines: List[str] = []

    def flush() -> None:
        body = "\n".join(body_lines).strip()
        if body:
            sections.append((title, body))

    for line in lines:
        if _is_heading_line(line):
            flush()
            title = line.strip()
            body_lines = []
        else:
            body_lines.append(line)
    flush()
    if not sections and text.strip():
        return [("", text.strip())]
    return sections


def _char_chunks(text: str, chunk_size: int, overlap: int) -> List[str]:
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


def chunk_manual_document(
    doc: Document,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> List[Document]:
    """Split one manual page into section-aware chunks with parent_id metadata."""
    meta = dict(doc.metadata or {})
    parent_id = manual_parent_id(meta)
    meta["parent_id"] = parent_id
    text = doc.page_content or ""
    sections = split_page_into_sections(text)
    out: List[Document] = []
    global_chunk = 0
    for section_idx, (section_title, body) in enumerate(sections):
        for local_idx, piece in enumerate(_char_chunks(body, chunk_size, chunk_overlap)):
            chunk_meta = dict(meta)
            chunk_meta["section_title"] = (section_title or "")[:200]
            chunk_meta["section_index"] = section_idx
            chunk_meta["chunk_index"] = global_chunk
            chunk_meta["chunk_id"] = f"{parent_id}:s{section_idx}:c{global_chunk}"
            out.append(Document(page_content=piece, metadata=chunk_meta))
            global_chunk += 1
            _ = local_idx
    return out
