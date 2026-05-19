"""BMW — digital owner's manuals require VIN on bmwusa.com (no public PDF)."""
from __future__ import annotations

from src.rag.sources.base import ManualAdapter


class BmwAdapter(ManualAdapter):
    def resolve_manual_url(self, make: str, model: str, year: int) -> str:
        raise ValueError(
            f"BMW does not publish a direct PDF for {year} {model} on bmwusa.com. "
            "Use https://www.bmwusa.com/owners-manuals.html with your VIN, or place "
            f"data/sources/manuals/BMW/{model}/{year}/owner_manual.pdf"
        )
