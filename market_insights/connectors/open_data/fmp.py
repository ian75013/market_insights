"""Financial Modeling Prep connector (free tier: 250 requests/day).

Provides:
- company profile, ratios, key metrics
- income / balance / cash flow statements
- stock screener
- earnings calendar, dividends

API key: https://site.financialmodelingprep.com/developer/docs (free)
"""

from __future__ import annotations

import logging

from market_insights.connectors.open_data.base import BaseHTTPConnector
from market_insights.core.cache import ttl_cache
from market_insights.core.config import settings

logger = logging.getLogger(__name__)

FMP_BASE = "https://financialmodelingprep.com/api/v3"


class FMPProfileConnector(BaseHTTPConnector):
    """Company profile from Financial Modeling Prep."""

    provider_name = "fmp_profile"

    def __init__(self, api_key: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.api_key = api_key or settings.fmp_api_key

    def available(self) -> bool:
        return bool(self.api_key) and self.use_network

    @ttl_cache(seconds=settings.cache_ttl_fundamentals, prefix="fmp_profile")
    def fetch(self, ticker: str) -> dict:
        if not self.available():
            raise ConnectionError("FMP: no API key or network disabled")

        url = f"{FMP_BASE}/profile/{ticker.upper()}?apikey={self.api_key}"
        logger.info("FMP: fetching %s profile", ticker)
        data = self.get_json(url, cache_key=f"fmp_profile:{ticker}")

        if not data or not isinstance(data, list) or len(data) == 0:
            raise ValueError(f"FMP returned no profile for {ticker}")

        p = data[0]
        return {
            "ticker": p.get("symbol", ticker.upper()),
            "name": p.get("companyName", ""),
            "sector": p.get("sector", ""),
            "industry": p.get("industry", ""),
            "market_cap": p.get("mktCap", 0),
            "currency": p.get("currency", "USD"),
            "exchange": p.get("exchangeShortName", ""),
            "pe": p.get("pe") or 0.0,
            "beta": p.get("beta") or 0.0,
            "price": p.get("price", 0.0),
            "dividend_yield": (p.get("lastDiv", 0.0) or 0.0) / max(p.get("price", 1.0), 0.01),
            "52w_high": p.get("range", "0-0").split("-")[-1].strip() if p.get("range") else 0.0,
            "52w_low": p.get("range", "0-0").split("-")[0].strip() if p.get("range") else 0.0,
            "avg_volume": p.get("volAvg", 0),
            "description": (p.get("description", "") or "")[:500],
            "website": p.get("website", ""),
            "country": p.get("country", ""),
            "ipo_date": p.get("ipoDate", ""),
            "is_etf": p.get("isEtf", False),
            "is_fund": p.get("isFund", False),
        }


class FMPRatiosConnector(BaseHTTPConnector):
    """Key financial ratios from FMP."""

    provider_name = "fmp_ratios"

    def __init__(self, api_key: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.api_key = api_key or settings.fmp_api_key

    def available(self) -> bool:
        return bool(self.api_key) and self.use_network

    @ttl_cache(seconds=settings.cache_ttl_fundamentals, prefix="fmp_ratios")
    def fetch(self, ticker: str) -> dict:
        if not self.available():
            raise ConnectionError("FMP: no API key or network disabled")

        url = f"{FMP_BASE}/ratios-ttm/{ticker.upper()}?apikey={self.api_key}"
        logger.info("FMP: fetching %s ratios TTM", ticker)
        data = self.get_json(url, cache_key=f"fmp_ratios:{ticker}")

        if not data or not isinstance(data, list) or len(data) == 0:
            raise ValueError(f"FMP returned no ratios for {ticker}")

        r = data[0]
        return {
            "pe": r.get("peRatioTTM", 0.0),
            "peg_ratio": r.get("pegRatioTTM", 0.0),
            "price_to_book": r.get("priceToBookRatioTTM", 0.0),
            "price_to_sales": r.get("priceToSalesRatioTTM", 0.0),
            "debt_to_equity": r.get("debtEquityRatioTTM", 0.0),
            "current_ratio": r.get("currentRatioTTM", 0.0),
            "return_on_equity": r.get("returnOnEquityTTM", 0.0),
            "return_on_assets": r.get("returnOnAssetsTTM", 0.0),
            "gross_margin": r.get("grossProfitMarginTTM", 0.0),
            "operating_margin": r.get("operatingProfitMarginTTM", 0.0),
            "profit_margin": r.get("netProfitMarginTTM", 0.0),
            "dividend_yield": r.get("dividendYieldTTM", 0.0),
        }


class FMPEarningsConnector(BaseHTTPConnector):
    """Earnings calendar from FMP."""

    provider_name = "fmp_earnings"

    def __init__(self, api_key: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.api_key = api_key or settings.fmp_api_key

    def available(self) -> bool:
        return bool(self.api_key) and self.use_network

    @ttl_cache(seconds=settings.cache_ttl_fundamentals, prefix="fmp_earnings")
    def fetch(self, ticker: str) -> list[dict]:
        if not self.available():
            raise ConnectionError("FMP: no API key or network disabled")

        url = f"{FMP_BASE}/historical/earning_calendar/{ticker.upper()}?limit=8&apikey={self.api_key}"
        logger.info("FMP: fetching %s earnings calendar", ticker)
        data = self.get_json(url, cache_key=f"fmp_earnings:{ticker}")

        if not isinstance(data, list):
            return []

        return [
            {
                "date": e.get("date", ""),
                "eps_estimated": e.get("epsEstimated"),
                "eps_actual": e.get("eps"),
                "revenue_estimated": e.get("revenueEstimated"),
                "revenue_actual": e.get("revenue"),
                "fiscal_period": e.get("fiscalDateEnding", ""),
            }
            for e in data[:8]
        ]
