"""One-off script to regenerate tests/fixtures/manual_sample.pdf."""
from pathlib import Path

try:
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, ArrayObject, NumberObject
except ImportError:
    raise SystemExit("pip install pypdf first")


def _minimal_pdf_with_text(text: str) -> bytes:
    """Build a minimal single-page PDF with embedded text (synthetic fixture)."""
    # Use reportlab-free approach: write raw PDF with text stream
    content = (
        "BT /F1 12 Tf 72 720 Td "
        + " ".join(f"({line.replace('(', '\\(').replace(')', '\\)')}) Tj 0 -16 Td" for line in text.split("\n"))
        + " ET"
    )
    objects = []
    xref = []

    def add_obj(s: str) -> int:
        objects.append(s)
        return len(objects)

    font_obj = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    content_obj = add_obj(f"<< /Length {len(content)} >>\nstream\n{content}\nendstream")
    page_obj = add_obj(
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        f"/Contents {content_obj} 0 R /Resources << /Font << /F1 {font_obj} 0 R >> >> >>"
    )
    pages_obj = add_obj(f"<< /Type /Pages /Kids [{page_obj} 0 R] /Count 1 >>")
    catalog_obj = add_obj(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>")

    out = ["%PDF-1.4\n"]
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len("".join(out).encode("latin-1")))
        out.append(f"{i} 0 obj\n{obj}\nendobj\n")
    xref_start = len("".join(out).encode("latin-1"))
    out.append(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n")
    for off in offsets[1:]:
        out.append(f"{off:010d} 00000 n \n")
    out.append(
        f"trailer\n<< /Size {len(objects)+1} /Root {catalog_obj} 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n"
    )
    return "".join(out).encode("latin-1", errors="replace")


def main() -> None:
    text = (
        "Owner Manual - Synthetic Test Fixture\n"
        "Tire Pressure: Recommended cold tire pressure is 32-35 PSI for sedans.\n"
        "Check the driver door jamb sticker for the exact specification.\n"
        "Maintenance: Oil change every 5,000-7,500 miles for conventional oil.\n"
        "Brake inspection every 10,000 miles. Never ignore warning lights."
    )
    path = Path(__file__).parent / "manual_sample.pdf"
    path.write_bytes(_minimal_pdf_with_text(text))
    print(f"Wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
