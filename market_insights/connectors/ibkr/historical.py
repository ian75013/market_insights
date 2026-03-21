from __future__ import annotations

import pandas as pd
from pathlib import Path

from market_insights.connectors.ibkr.client import IBClient


SAMPLE_PRICES = Path(__file__).resolve().parents[2] / "data" / "sample" / "prices.csv"


class IBHistoricalFetcher:
    def __init__(self, client: IBClient | None = None) -> None:
        self.client = client or IBClient()

    def fetch_prices(self, ticker: str, duration: str = "6 M", bar_size: str = "1 day") -> pd.DataFrame:
        if not self.client.connect():
            return self._fallback_sample(ticker)

        try:
            from ib_insync import Stock, util  # type: ignore
            contract = Stock(ticker.upper(), "SMART", "USD")
            bars = self.client._ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow="TRADES",
                useRTH=True,
                formatDate=1,
            )
            df = util.df(bars)
            if df.empty:
                return self._fallback_sample(ticker)
            out = df.rename(columns={"date": "date", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"})
            out["ticker"] = ticker.upper()
            return out[["ticker", "date", "open", "high", "low", "close", "volume"]]
        except Exception:
            return self._fallback_sample(ticker)
        finally:
            self.client.disconnect()

    def _fallback_sample(self, ticker: str) -> pd.DataFrame:
        df = pd.read_csv(SAMPLE_PRICES, parse_dates=["date"])
        df = df[df["ticker"].str.upper() == ticker.upper()].copy()
        if df.empty:
            raise ValueError(f"No sample data for ticker={ticker}")
        return df
