from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "sample" / "prices.csv"


def fetch_sample_prices(ticker: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    return df[df["ticker"] == ticker].copy()
