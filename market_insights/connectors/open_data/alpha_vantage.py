"""Alpha Vantage connector (free tier: 25 requests/day).

Provides:
- daily / intraday OHLCV prices
- company overview (fundamentals, ratios)
- income statements, balance sheets, cash flows
- earnings calendar
- news & sentiment

API key: https://www.alphavantage.co/support/#api-key (free)
"""

from __future__ import annotations

import logging
from io import StringIO

import pandas as pd

from market_insights.connectors.open_data.base import BaseHTTPConnector
from market_insights.core.cache import ttl_cache
from market_insights.core.config import settings

logger = logging.getLogger(__name__)

AV_BASE = "https://www.alphavantage.co/query"


class AlphaVantagePriceConnector(BaseHTTPConnector):
    """Fetch daily adjusted prices from Alpha Vantage."""

    provider_name = "alpha_vantage"

    def __init__(self, api_key: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.api_key = api_key or settings.alpha_vantage_api_key

    def available(self) -> bool:
        return bool(self.api_key) and self.use_network

    @ttl_cache(seconds=settings.cache_ttl_prices, prefix="av_prices")
    def fetch(self, ticker: str, outputsize: str = "compact") -> pd.DataFrame:
        if not self.available():
            raise ConnectionError("Alpha Vantage: no API key or network disabled")

        url = (
            f"{AV_BASE}?function=TIME_SERIES_DAILY"
            f"&symbol={ticker.upper()}"
            f"&outputsize={outputsize}"
            f"&datatype=csv"
            f"&apikey={self.api_key}"
        )
        logger.info("AlphaVantage: fetching %s daily prices", ticker)
        csv_text = self.get_csv_text(
            url, cache_key=f"av_prices_csv:{ticker}:{outputsize}"
        )

        df = pd.read_csv(StringIO(csv_text))
        if df.empty or "timestamp" not in df.columns:
            raise ValueError(f"AlphaVantage returned no data for {ticker}")

        df = df.rename(columns={"timestamp": "date"})
        df["ticker"] = ticker.upper()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        cols = ["ticker", "date", "open", "high", "low", "close", "volume"]
        for c in cols:
            if c not in df.columns:
                df[c] = 0
        return df[cols].copy()


class AlphaVantageOverviewConnector(BaseHTTPConnector):
    """Fetch company overview / fundamentals from Alpha Vantage."""

    provider_name = "alpha_vantage_overview"

    def __init__(self, api_key: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.api_key = api_key or settings.alpha_vantage_api_key

    def available(self) -> bool:
        return bool(self.api_key) and self.use_network

    @ttl_cache(seconds=settings.cache_ttl_fundamentals, prefix="av_overview")
    def fetch(self, ticker: str) -> dict:
        if not self.available():
            raise ConnectionError("Alpha Vantage: no API key or network disabled")

        url = (
            f"{AV_BASE}?function=OVERVIEW&symbol={ticker.upper()}&apikey={self.api_key}"
        )
        logger.info("AlphaVantage: fetching %s overview", ticker)
        data = self.get_json(url, cache_key=f"av_overview:{ticker}")

        if not data or "Symbol" not in data:
            raise ValueError(f"AlphaVantage returned no overview for {ticker}")

        def _float(key: str, default: float = 0.0) -> float:
            try:
                return float(data.get(key, default))
            except (ValueError, TypeError):
                return default

        return {
            "ticker": data.get("Symbol", ticker.upper()),
            "name": data.get("Name", ""),
            "sector": data.get("Sector", ""),
            "industry": data.get("Industry", ""),
            "market_cap": _float("MarketCapitalization"),
            "pe": _float("PERatio"),
            "forward_pe": _float("ForwardPE"),
            "peg_ratio": _float("PEGRatio"),
            "price_to_book": _float("PriceToBookRatio"),
            "eps_trailing": _float("EPS"),
            "revenue_growth": _float("QuarterlyRevenueGrowthYOY"),
            "earnings_growth": _float("QuarterlyEarningsGrowthYOY"),
            "eps_growth": _float("QuarterlyEarningsGrowthYOY"),
            "profit_margin": _float("ProfitMargin"),
            "operating_margin": _float("OperatingMarginTTM"),
            "gross_margin": 0.0,
            "debt_to_equity": 0.0,
            "return_on_equity": _float("ReturnOnEquityTTM"),
            "return_on_assets": _float("ReturnOnAssetsTTM"),
            "dividend_yield": _float("DividendYield"),
            "beta": _float("Beta"),
            "52w_high": _float("52WeekHigh"),
            "52w_low": _float("52WeekLow"),
            "description": (data.get("Description", "") or "")[:500],
        }


class AlphaVantageNewsConnector(BaseHTTPConnector):
    """Fetch news & sentiment from Alpha Vantage."""

    provider_name = "alpha_vantage_news"

    def __init__(self, api_key: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.api_key = api_key or settings.alpha_vantage_api_key

    def available(self) -> bool:
        return bool(self.api_key) and self.use_network

    @ttl_cache(seconds=settings.cache_ttl_news, prefix="av_news")
    def fetch(self, ticker: str, limit: int = 10) -> list[dict]:
        if not self.available():
            raise ConnectionError("Alpha Vantage: no API key or network disabled")

        url = (
            f"{AV_BASE}?function=NEWS_SENTIMENT"
            f"&tickers={ticker.upper()}"
            f"&limit={limit}"
            f"&apikey={self.api_key}"
        )
        logger.info("AlphaVantage: fetching %s news sentiment", ticker)
        data = self.get_json(url, cache_key=f"av_news:{ticker}:{limit}")

        items = []
        for feed in (data.get("feed") or [])[:limit]:
            sentiment_score = 0.0
            for ts in feed.get("ticker_sentiment", []):
                if ts.get("ticker", "").upper() == ticker.upper():
                    try:
                        sentiment_score = float(ts.get("ticker_sentiment_score", 0))
                    except (ValueError, TypeError):
                        pass
                    break

            items.append(
                {
                    "title": feed.get("title", ""),
                    "link": feed.get("url", ""),
                    "published_at": feed.get("time_published", ""),
                    "content": (feed.get("summary", "") or "")[:400],
                    "source": feed.get("source", ""),
                    "sentiment_score": sentiment_score,
                    "sentiment_label": feed.get("overall_sentiment_label", ""),
                }
            )
        return items
