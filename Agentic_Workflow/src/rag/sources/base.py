"""Base class for OEM manual download adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod


class ManualAdapter(ABC):
    """Resolve official owner-manual PDF URLs for a vehicle."""

    @abstractmethod
    def resolve_manual_url(self, make: str, model: str, year: int) -> str:
        """Return a direct PDF URL or raise if unavailable."""
