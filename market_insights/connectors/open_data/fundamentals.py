"""Multi-source fundamentals connector with cascading fallback.

Resolution order:
1. Yahoo Finance (yfinance) — if installed and network enabled
2. Alpha Vantage — if API key present and network enabled
3. Financial Modeling Prep — if API key present and network enabled
4. SEC EDGAR — if network enabled (no key required)
5. Sample data — always available (offline demo)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from market_insights.connectors.open_data.base import BaseHTTPConnector
from market_insights.core.cache import ttl_cache
from market_insights.core.config import settings

logger = logging.getLogger(__name__)

SAMPLE_FILE = (
    Path(__file__).resolve().parents[2] / "data" / "sample" / "fundamentals.json"
)

# CIK lookup for common tickers (SEC EDGAR)
TICKER_TO_CIK = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "NVDA": "0001045810",
    "META": "0001326801",
    "TSLA": "0001318605",
    "JPM": "0000019617",
    "V": "0001403161",
    "JNJ": "0000200406",
    "WMT": "0000104169",
    "PG": "0000080424",
    "MA": "0001141391",
    "UNH": "0000731766",
    "HD": "0000354950",
    "DIS": "0001744489",
    "BAC": "0000070858",
    "NFLX": "0001065280",
    "INTC": "0000050863",
    "AMD": "0000002488",
    "CRM": "0001108524",
}


class SampleFundamentalsConnector:
    """Offline fundamentals from enriched sample data."""

    provider_name = "sample_fundamentals"

    def fetch(self, ticker: str) -> dict:
        data = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
        try:
            return data[ticker.upper()]
        except KeyError as exc:
            raise ValueError(f"No sample fundamentals for ticker={ticker}") from exc


class SECCompanyFactsConnector(BaseHTTPConnector):
    """SEC EDGAR company facts — free, no API key, just a User-Agent header."""

    provider_name = "sec_edgar"

    def __init__(self, **kwargs) -> None:
        super().__init__(cache_ttl=settings.cache_ttl_fundamentals, **kwargs)

    def available(self) -> bool:
        return self.use_network

    @ttl_cache(seconds=settings.cache_ttl_fundamentals, prefix="sec_facts")
    def fetch(self, ticker: str) -> dict:
        if not self.available():
            raise ConnectionError("SEC: network disabled")

        cik = TICKER_TO_CIK.get(ticker.upper())
        if not cik:
            raise ValueError(f"No CIK mapping for ticker={ticker}")

        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        logger.info("SEC EDGAR: fetching company facts for %s (CIK %s)", ticker, cik)
        data = self.get_json(url, cache_key=f"sec_facts:{cik}")

        facts = data.get("facts", {})
        us_gaap = facts.get("us-gaap", {})

        def _latest_value(concept: str) -> float | None:
            units = us_gaap.get(concept, {}).get("units", {})
            for unit_type in ("USD", "USD/shares", "pure"):
                entries = units.get(unit_type, [])
                if entries:
                    # Sort by end date and return most recent
                    sorted_entries = sorted(
                        entries, key=lambda x: x.get("end", ""), reverse=True
                    )
                    try:
                        return float(sorted_entries[0].get("val", 0))
                    except (ValueError, TypeError):
                        continue
            return None

        revenue = (
            _latest_value("Revenues")
            or _latest_value("RevenueFromContractWithCustomerExcludingAssessedTax")
            or 0
        )
        net_income = _latest_value("NetIncomeLoss") or 0
        total_assets = _latest_value("Assets") or 1
        total_liabilities = _latest_value("Liabilities") or 0
        equity = _latest_value("StockholdersEquity") or 1
        eps = _latest_value("EarningsPerShareDiluted") or 0

        return {
            "ticker": ticker.upper(),
            "source": "sec_edgar",
            "revenue": revenue,
            "net_income": net_income,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "equity": equity,
            "eps_diluted": eps,
            "debt_to_equity": round(total_liabilities / max(equity, 1), 4),
            "profit_margin": round(net_income / max(revenue, 1), 4) if revenue else 0,
            "return_on_assets": round(net_income / max(total_assets, 1), 4),
            "return_on_equity": round(net_income / max(equity, 1), 4),
        }


class MultiFundamentalsConnector:
    """Cascading fundamentals connector: tries each source in priority order."""

    provider_name = "multi_fundamentals"

    def fetch(self, ticker: str) -> dict:
        errors: list[str] = []

        # 1. Yahoo Finance
        try:
            from market_insights.connectors.open_data.yahoo import (
                YFinanceFundamentalsConnector,
            )

            conn = YFinanceFundamentalsConnector()
            if conn.available():
                result = conn.fetch(ticker)
                if result and result.get("pe", 0) > 0:
                    result["_source"] = "yahoo"
                    logger.info(
                        "Fundamentals for %s resolved via Yahoo Finance", ticker
                    )
                    return result
        except Exception as exc:
            errors.append(f"yahoo: {exc}")

        # 2. Alpha Vantage
        try:
            from market_insights.connectors.open_data.alpha_vantage import (
                AlphaVantageOverviewConnector,
            )

            conn = AlphaVantageOverviewConnector()
            if conn.available():
                result = conn.fetch(ticker)
                if result and result.get("name"):
                    result["_source"] = "alpha_vantage"
                    logger.info(
                        "Fundamentals for %s resolved via Alpha Vantage", ticker
                    )
                    return result
        except Exception as exc:
            errors.append(f"alpha_vantage: {exc}")

        # 3. Financial Modeling Prep
        try:
            from market_insights.connectors.open_data.fmp import FMPProfileConnector

            conn = FMPProfileConnector()
            if conn.available():
                result = conn.fetch(ticker)
                if result and result.get("name"):
                    result["_source"] = "fmp"
                    logger.info("Fundamentals for %s resolved via FMP", ticker)
                    return result
        except Exception as exc:
            errors.append(f"fmp: {exc}")

        # 4. SEC EDGAR
        try:
            conn = SECCompanyFactsConnector()
            if conn.available():
                result = conn.fetch(ticker)
                if result:
                    result["_source"] = "sec_edgar"
                    logger.info("Fundamentals for %s resolved via SEC EDGAR", ticker)
                    return result
        except Exception as exc:
            errors.append(f"sec: {exc}")

        # 5. Sample fallback
        try:
            result = SampleFundamentalsConnector().fetch(ticker)
            result["_source"] = "sample"
            logger.info("Fundamentals for %s resolved via sample data", ticker)
            return result
        except Exception as exc:
            errors.append(f"sample: {exc}")

        raise ValueError(
            f"No fundamentals found for {ticker}. Errors: {'; '.join(errors)}"
        )
