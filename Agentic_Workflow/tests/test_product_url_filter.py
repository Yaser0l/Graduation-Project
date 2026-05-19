"""Tests for product URL filtering (PDP vs category pages)."""
from __future__ import annotations

from src.tools.tavily_tool import _is_product_page_url, _score_product_result


class TestProductUrlFilter:
    def test_rejects_walmart_category(self):
        url = "https://www.walmart.com/c/auto/toyota-camry-tire-pressure-monitoring-system-tpms-sensor"
        assert not _is_product_page_url(url)

    def test_accepts_amazon_dp(self):
        url = "https://www.amazon.com/dp/B08XYZ12345"
        assert _is_product_page_url(url)

    def test_accepts_oem_parts_path(self):
        url = "https://parts.lakelandtoyota.com/p/toyota_2020_CAMRY/Switch-Pressure-Vacuum-Sensor-Brake/14776794/8339028120.html"
        assert _is_product_page_url(url)

    def test_score_prefers_pdp(self):
        good = _score_product_result({"url": "https://www.amazon.com/dp/B123", "title": "TPMS Sensor OEM"})
        bad = _score_product_result(
            {"url": "https://www.walmart.com/c/auto/tpms", "title": "TPMS category"}
        )
        assert good > bad
