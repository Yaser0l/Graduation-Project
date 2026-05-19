"""Per-OEM manual URL resolvers (official OEM domains only)."""
from __future__ import annotations

from typing import Dict

from src.rag.sources.base import ManualAdapter
from src.rag.sources import (
    bmw,
    ford,
    gm,
    honda,
    hyundai,
    kia,
    mercedes,
    nissan,
    toyota,
)

_ADAPTERS: Dict[str, ManualAdapter] = {
    "toyota": toyota.ToyotaAdapter(),
    "honda": honda.HondaAdapter(),
    "ford": ford.FordAdapter(),
    "gm": gm.GmAdapter(),
    "chevrolet": gm.GmAdapter(),
    "chevy": gm.GmAdapter(),
    "nissan": nissan.NissanAdapter(),
    "hyundai": hyundai.HyundaiAdapter(),
    "kia": kia.KiaAdapter(),
    "bmw": bmw.BmwAdapter(),
    "mercedes": mercedes.MercedesAdapter(),
    "mercedes-benz": mercedes.MercedesAdapter(),
    "mb": mercedes.MercedesAdapter(),
}


def get_adapter(name: str) -> ManualAdapter:
    key = (name or "").strip().lower()
    if key in _ADAPTERS:
        return _ADAPTERS[key]
    raise KeyError(f"Unknown manual adapter: {name!r}")
