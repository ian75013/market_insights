"""Price connectors: Sample, Stooq, Yahoo Finance, Alpha Vantage, CoinGecko.

Resolution order in PriceProviderRouter:
- explicit provider name → use that provider
- "auto" → try Yahoo → Stooq → Alpha Vantage → CoinGecko → Sample
"""

from __future__ import annotations

import logging
from io import StringIO
from pathlib import Path

import pandas as pd

from market_insights.connectors.open_data.base import BaseHTTPConnector
from market_insights.core.cache import ttl_cache
from market_insights.core.config import settings

logger = logging.getLogger(__name__)

SAMPLE_PRICES = Path(__file__).resolve().parents[2] / "data" / "sample" / "prices.csv"


class SamplePriceConnector:
    provider_name = "sample"

    def fetch(self, ticker: str) -> pd.DataFrame:
        df = pd.read_csv(SAMPLE_PRICES, parse_dates=["date"])
        df = df[df["ticker"].str.upper() == ticker.upper()].copy()
        if df.empty:
            raise ValueError(f"No sample data for ticker={ticker}")
        return df


class StooqPriceConnector(BaseHTTPConnector):
    """Stooq.com — free daily EOD prices, no API key."""

    provider_name = "stooq"

    def __init__(self, **kwargs) -> None:
        super().__init__(cache_ttl=settings.cache_ttl_prices, **kwargs)

    @ttl_cache(seconds=settings.cache_ttl_prices, prefix="stooq_prices")
    def fetch(self, ticker: str) -> pd.DataFrame:
        if not self.use_network:
            return SamplePriceConnector().fetch(ticker)

        symbol = f"{ticker.lower()}.us"
        url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
        logger.info("Stooq: fetching %s daily prices", ticker)
        csv_text = self.get_csv_text(url, cache_key=f"stooq:{symbol}")

        df = pd.read_csv(StringIO(csv_text))
        if df.empty or len(df.columns) < 5:
            raise ValueError(f"Stooq returned no data for {ticker}")

        df.columns = [c.lower() for c in df.columns]
        df["ticker"] = ticker.upper()
        df = df.rename(columns={
            "date": "date", "open": "open", "high": "high",
            "low": "low", "close": "close", "volume": "volume",
        })
        df["date"] = pd.to_datetime(df["date"])
        if "volume" not in df.columns:
            df["volume"] = 0
        return df[["ticker", "date", "open", "high", "low", "close", "volume"]].sort_values("date").reset_index(drop=True)
