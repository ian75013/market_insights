from __future__ import annotations

from pathlib import Path
import json

from market_insights.connectors.open_data.base import BaseHTTPConnector


SAMPLE_FILE = Path(__file__).resolve().parents[2] / "data" / "sample" / "fundamentals.json"


class SampleFundamentalsConnector:
    provider_name = "sample_fundamentals"

    def fetch(self, ticker: str) -> dict:
        data = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
        try:
            return data[ticker.upper()]
        except KeyError as exc:
            raise ValueError(f"No fundamentals found for ticker={ticker}") from exc


class SECCompanyFactsConnector(BaseHTTPConnector):
    provider_name = "sec_company_facts"

    def fetch(self, cik: str | None = None, ticker: str | None = None) -> dict:
        if not self.use_network or not cik:
            if not ticker:
                raise ValueError("ticker is required when use_network is false")
            return SampleFundamentalsConnector().fetch(ticker)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"
        return self.get_json(url)
