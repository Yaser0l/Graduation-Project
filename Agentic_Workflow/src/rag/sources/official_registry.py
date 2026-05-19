"""Verified official OEM owner-manual PDF URLs (OEM domains only)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class OfficialManual:
    url: str
    publisher: str
    doc_kind: str = "owner_manual"  # owner_manual | handbook | quick_reference
    referer: Optional[str] = None
    notes: Optional[str] = None


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s


def _registry_key(make: str, model: str, year: int) -> Tuple[str, str, int]:
    return (_slug(make), _slug(model), int(year))


# Keys: (make_slug, model_slug, year) -> OfficialManual
# Sources: OEM CDNs (Honda techinfo, Ford fordservicecontent, GM contentdelivery, etc.)
OFFICIAL_MANUALS: Dict[Tuple[str, str, int], OfficialManual] = {
    (_slug("Toyota"), _slug("Camry"), 2020): OfficialManual(
        url="https://assets.sia.toyota.com/publications/en/om-s/OM06158U/pdf/OM06158U.pdf",
        publisher="Toyota Motor Sales (assets.sia.toyota.com)",
        referer="https://www.toyota.com/owners/warranty-owners-manuals/vehicle/camry/2020/",
        notes="Full 2020 Camry OM; CDN may return 403 from some networks — use TIS or local PDF fallback.",
    ),
    (_slug("Honda"), _slug("Accord"), 2020): OfficialManual(
        url="https://techinfo.honda.com/rjanisis/pubs/OM/AH/ATWA2121OM/enu/ATWA2121OM.PDF",
        publisher="American Honda Motor (techinfo.honda.com)",
        referer="https://techinfo.honda.com/",
    ),
    (_slug("Ford"), _slug("F-150"), 2020): OfficialManual(
        url=(
            "https://www.fordservicecontent.com/Ford_Content/Catalog/owner_information/"
            "2020-Ford-F-150-Owners-Manual-version3_om_EN-US_04_2020.pdf"
        ),
        publisher="Ford Motor Company (fordservicecontent.com)",
        referer="https://www.ford.com/support/owner-manuals/",
    ),
    (_slug("Chevrolet"), _slug("Silverado"), 2020): OfficialManual(
        url=(
            "https://contentdelivery.ext.gm.com/bypass/gma-content-api/resources/sites/GMA/"
            "content/staging/MANUALS/4000/MA4988/en_US/2.0/"
            "20_CHEV_Silverado_OM_en_US_U_84186886C_2020JAN30_3P.pdf"
        ),
        publisher="General Motors (contentdelivery.ext.gm.com)",
        referer="https://www.chevrolet.com/",
    ),
    (_slug("Nissan"), _slug("Altima"), 2020): OfficialManual(
        url=(
            "https://www.nissanusa.com/content/dam/Nissan/us/manuals-and-guides/"
            "altima/2020/2020-nissan-altima-owner-manual.pdf"
        ),
        publisher="Nissan North America (nissanusa.com)",
        referer="https://www.nissanusa.com/",
    ),
    (_slug("Hyundai"), _slug("Sonata"), 2020): OfficialManual(
        url=(
            "https://owners.hyundaiusa.com/content/dam/hyundai/us/myhyundai/manuals/"
            "glovebox-manual/2020/owners-handbook-warranty/2020_Owners_Handbook_Warranty_r2.pdf"
        ),
        publisher="Hyundai Motor America (owners.hyundaiusa.com)",
        doc_kind="handbook",
        referer="https://owners.hyundaiusa.com/",
        notes="Official glovebox handbook + warranty; full 2020 Sonata OM is not on a public PDF CDN.",
    ),
    (_slug("Kia"), _slug("Optima"), 2020): OfficialManual(
        url="https://owners.kia.com/content/dam/kia/us/owners/pdf/2020/2020-Kia-Optima.pdf",
        publisher="Kia America (owners.kia.com)",
        referer="https://owners.kia.com/",
    ),
    (_slug("Mercedes-Benz"), _slug("C-Class"), 2020): OfficialManual(
        url=(
            "https://www.mbusa.com/content/dam/mb-nafta/us/owners/manuals/2020/Operators/"
            "2020_C-Class_Sedan_OM.pdf"
        ),
        publisher="Mercedes-Benz USA (mbusa.com)",
        referer="https://www.mbusa.com/",
    ),
}


def lookup_official_manual(make: str, model: str, year: int) -> Optional[OfficialManual]:
    key = _registry_key(make, model, year)
    if key in OFFICIAL_MANUALS:
        return OFFICIAL_MANUALS[key]
    # Aliases
    aliases = {
        (_slug("Mercedes"), _slug("C-Class"), 2020): (_slug("Mercedes-Benz"), _slug("C-Class"), 2020),
        (_slug("Chevy"), _slug("Silverado"), 2020): (_slug("Chevrolet"), _slug("Silverado"), 2020),
    }
    alt = aliases.get(key)
    if alt:
        return OFFICIAL_MANUALS.get(alt)
    return None


def list_supported() -> List[Tuple[str, str, int]]:
    return [(m, mod, y) for (m, mod, y) in OFFICIAL_MANUALS]
