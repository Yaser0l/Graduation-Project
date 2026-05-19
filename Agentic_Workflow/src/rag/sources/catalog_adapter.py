"""Resolve manuals from the official OEM URL registry."""
from __future__ import annotations

from src.rag.sources.base import ManualAdapter
from src.rag.sources.official_registry import OfficialManual, lookup_official_manual


class CatalogAdapter(ManualAdapter):
    """Look up verified OEM PDF URLs by make / model / year."""

    def resolve_manual(self, make: str, model: str, year: int) -> OfficialManual:
        entry = lookup_official_manual(make, model, year)
        if not entry:
            raise ValueError(
                f"No official manual URL registered for {year} {make} {model}. "
                f"Add an entry to official_registry.py or place a PDF under "
                f"data/sources/manuals/{make}/{model}/{year}/owner_manual.pdf"
            )
        return entry

    def resolve_manual_url(self, make: str, model: str, year: int) -> str:
        return self.resolve_manual(make, model, year).url

    def resolve_referer(self, make: str, model: str, year: int) -> str | None:
        return self.resolve_manual(make, model, year).referer
