"""Yahoo Finance connector via yfinance.

yfinance is the most reliable free source for:
- daily / weekly / monthly OHLCV prices
- company info (sector, industry, market cap, description)
- key financial ratios (P/E, EPS, debt/equity, margins)
- dividends and splits history

Install: pip install yfinance
Limits : no official rate limit but aggressive scraping may get throttled.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pandas as pd

from market_insights.core.cache import ttl_cache
from market_insights.core.config import settings

logger = logging.getLogger(__name__)

_YFINANCE_AVAILABLE = False
try:
    import yfinance as yf  # type: ignore

    _YFINANCE_AVAILABLE = True
except ImportError:
    yf = None  # type: ignore


class YFinancePriceConnector:
    """Fetch OHLCV prices from Yahoo Finance."""

    provider_name = "yahoo"

    @staticmethod
    def available() -> bool:
        return _YFINANCE_AVAILABLE

    @ttl_cache(seconds=settings.cache_ttl_prices, prefix="yf_prices")
    def fetch(self, ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        if not _YFINANCE_AVAILABLE:
            raise ImportError("yfinance is not installed. Run: pip install yfinance")

        logger.info("YFinance: fetching %s prices (%s / %s)", ticker, period, interval)
        tk = yf.Ticker(ticker.upper())
        df = tk.history(period=period, interval=interval, auto_adjust=True)

        if df.empty:
            raise ValueError(f"YFinance returned no data for {ticker}")

        df = df.reset_index()
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        # yfinance returns 'date' or 'datetime' depending on interval
        date_col = "datetime" if "datetime" in df.columns else "date"
        df = df.rename(columns={date_col: "date"})
        df["ticker"] = ticker.upper()
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)

        cols = ["ticker", "date", "open", "high", "low", "close", "volume"]
        for c in cols:
            if c not in df.columns:
                df[c] = 0
        return df[cols].copy()


class YFinanceFundamentalsConnector:
    """Fetch company fundamentals from Yahoo Finance."""

    provider_name = "yahoo_fundamentals"

    @staticmethod
    def available() -> bool:
        return _YFINANCE_AVAILABLE

    @ttl_cache(seconds=settings.cache_ttl_fundamentals, prefix="yf_fundamentals")
    def fetch(self, ticker: str) -> dict:
        if not _YFINANCE_AVAILABLE:
            raise ImportError("yfinance is not installed. Run: pip install yfinance")

        logger.info("YFinance: fetching %s fundamentals", ticker)
        tk = yf.Ticker(ticker.upper())
        info = tk.info or {}

        return {
            "ticker": ticker.upper(),
            "name": info.get("longName", info.get("shortName", ticker.upper())),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "market_cap": info.get("marketCap", 0),
            "currency": info.get("currency", "USD"),
            "pe": info.get("trailingPE") or info.get("forwardPE") or 0.0,
            "forward_pe": info.get("forwardPE", 0.0),
            "peg_ratio": info.get("pegRatio", 0.0),
            "price_to_book": info.get("priceToBook", 0.0),
            "eps_trailing": info.get("trailingEps", 0.0),
            "eps_forward": info.get("forwardEps", 0.0),
            "revenue_growth": info.get("revenueGrowth", 0.0),
            "earnings_growth": info.get("earningsGrowth", 0.0),
            "eps_growth": info.get("earningsQuarterlyGrowth", 0.0),
            "profit_margin": info.get("profitMargins", 0.0),
            "operating_margin": info.get("operatingMargins", 0.0),
            "gross_margin": info.get("grossMargins", 0.0),
            "debt_to_equity": (info.get("debtToEquity", 0.0) or 0.0) / 100.0,
            "current_ratio": info.get("currentRatio", 0.0),
            "return_on_equity": info.get("returnOnEquity", 0.0),
            "return_on_assets": info.get("returnOnAssets", 0.0),
            "dividend_yield": info.get("dividendYield", 0.0),
            "beta": info.get("beta", 0.0),
            "52w_high": info.get("fiftyTwoWeekHigh", 0.0),
            "52w_low": info.get("fiftyTwoWeekLow", 0.0),
            "avg_volume": info.get("averageVolume", 0),
            "shares_outstanding": info.get("sharesOutstanding", 0),
            "description": (info.get("longBusinessSummary", "") or "")[:500],
        }


class YFinanceInfoConnector:
    """Fetch lightweight company profile from Yahoo Finance."""

    provider_name = "yahoo_info"

    @staticmethod
    def available() -> bool:
        return _YFINANCE_AVAILABLE

    @ttl_cache(seconds=3600, prefix="yf_info")
    def fetch(self, ticker: str) -> dict:
        if not _YFINANCE_AVAILABLE:
            raise ImportError("yfinance is not installed")

        tk = yf.Ticker(ticker.upper())
        info = tk.info or {}
        return {
            "ticker": ticker.upper(),
            "name": info.get("longName", ticker.upper()),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "exchange": info.get("exchange", ""),
            "market_cap": info.get("marketCap", 0),
            "currency": info.get("currency", "USD"),
            "website": info.get("website", ""),
            "description": (info.get("longBusinessSummary", "") or "")[:800],
        }
