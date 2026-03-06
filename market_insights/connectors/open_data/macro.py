from __future__ import annotations

from pathlib import Path
import json

from market_insights.connectors.open_data.base import BaseHTTPConnector


SAMPLE_MACRO = Path(__file__).resolve().parents[2] / "data" / "sample" / "macro.json"


class SampleMacroConnector:
    provider_name = "sample_macro"

    def fetch(self) -> dict:
        return json.loads(SAMPLE_MACRO.read_text(encoding="utf-8"))


class FREDConnector(BaseHTTPConnector):
    provider_name = "fred"

    def fetch_series(self, series_id: str) -> dict:
        if not self.use_network:
            return SampleMacroConnector().fetch()
        return self.get_json(f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&file_type=json")
