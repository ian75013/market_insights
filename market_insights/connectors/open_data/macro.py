"""Macro data connectors: FRED (with real API), ECB, and enriched sample.

FRED API key: https://fred.stlouisfed.org/docs/api/api_key.html (free)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from market_insights.connectors.open_data.base import BaseHTTPConnector
from market_insights.core.cache import ttl_cache
from market_insights.core.config import settings

logger = logging.getLogger(__name__)

SAMPLE_MACRO = Path(__file__).resolve().parents[2] / "data" / "sample" / "macro.json"

FRED_BASE = "https://api.stlouisfed.org/fred"

# Key macro series available on FRED
FRED_SERIES = {
    "fed_funds": "FEDFUNDS",
    "cpi_yoy": "CPIAUCSL",
    "gdp_real": "GDPC1",
    "unemployment": "UNRATE",
    "treasury_10y": "DGS10",
    "treasury_2y": "DGS2",
    "treasury_3m": "DTB3",
    "sp500": "SP500",
    "vix": "VIXCLS",
    "pce_core": "PCEPILFE",
    "housing_starts": "HOUST",
    "retail_sales": "RSXFS",
    "industrial_production": "INDPRO",
    "consumer_sentiment": "UMCSENT",
    "initial_claims": "ICSA",
    "m2_money_supply": "M2SL",
}


class SampleMacroConnector:
    provider_name = "sample_macro"

    def fetch(self) -> dict:
        return json.loads(SAMPLE_MACRO.read_text(encoding="utf-8"))


class FREDConnector(BaseHTTPConnector):
    """Real FRED API connector with proper key management."""

    provider_name = "fred"

    def __init__(self, api_key: str = "", **kwargs) -> None:
        super().__init__(cache_ttl=settings.cache_ttl_macro, **kwargs)
        self.api_key = api_key or settings.fred_api_key

    def available(self) -> bool:
        return bool(self.api_key) and self.use_network

    @ttl_cache(seconds=settings.cache_ttl_macro, prefix="fred_series")
    def fetch_series(
        self, series_id: str, limit: int = 60, sort_order: str = "desc"
    ) -> list[dict]:
        """Fetch a single FRED series — returns list of {date, value} dicts."""
        if not self.available():
            raise ConnectionError("FRED: no API key or network disabled")

        url = (
            f"{FRED_BASE}/series/observations"
            f"?series_id={series_id}"
            f"&sort_order={sort_order}"
            f"&limit={limit}"
            f"&file_type=json"
            f"&api_key={self.api_key}"
        )
        logger.info("FRED: fetching series %s", series_id)
        data = self.get_json(url, cache_key=f"fred:{series_id}:{limit}")

        observations = data.get("observations", [])
        result = []
        for obs in observations:
            val = obs.get("value", ".")
            if val == ".":
                continue
            try:
                result.append({"date": obs["date"], "value": float(val)})
            except (ValueError, TypeError):
                continue
        return result

    def fetch_latest(self, series_id: str) -> float | None:
        """Get the most recent value for a series."""
        try:
            obs = self.fetch_series(series_id, limit=1)
            return obs[0]["value"] if obs else None
        except Exception:
            return None

    def fetch_macro_dashboard(self) -> dict:
        """Fetch all key macro indicators in one call."""
        if not self.available():
            return SampleMacroConnector().fetch()

        dashboard = {}
        for name, series_id in FRED_SERIES.items():
            try:
                val = self.fetch_latest(series_id)
                if val is not None:
                    dashboard[name] = val
            except Exception as exc:
                logger.warning("FRED: failed to fetch %s: %s", name, exc)

        return dashboard

    def fetch_series_history(self, series_id: str, limit: int = 252) -> list[dict]:
        """Fetch historical series for charting."""
        return self.fetch_series(series_id, limit=limit, sort_order="asc")
