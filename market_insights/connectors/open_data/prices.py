from __future__ import annotations

from io import StringIO
from pathlib import Path
import pandas as pd

from market_insights.connectors.open_data.base import BaseHTTPConnector


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
    provider_name = "stooq"

    def fetch(self, ticker: str) -> pd.DataFrame:
        if not self.use_network:
            return SamplePriceConnector().fetch(ticker)
        symbol = f"{ticker.lower()}.us"
        csv_text = self.get_text(f"https://stooq.com/q/d/l/?s={symbol}&i=d")
        df = pd.read_csv(StringIO(csv_text))
        df.columns = [c.lower() for c in df.columns]
        df["ticker"] = ticker.upper()
        df = df.rename(columns={"date": "date", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"})
        df["date"] = pd.to_datetime(df["date"])
        return df[["ticker", "date", "open", "high", "low", "close", "volume"]]
