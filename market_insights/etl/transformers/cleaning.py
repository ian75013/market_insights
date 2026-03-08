from __future__ import annotations

import pandas as pd


PRICE_COLS = ["open", "high", "low", "close", "volume"]


def clean_market_data(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.drop_duplicates(subset=["ticker", "date"]).sort_values("date").reset_index(drop=True)

    for col in PRICE_COLS:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out["close"] = out["close"].ffill().bfill()
    for col in ["open", "high", "low"]:
        out[col] = out[col].fillna(out["close"])
    out["volume"] = out["volume"].fillna(0)

    out = out[(out["close"] > 0) & (out["high"] > 0) & (out["low"] > 0)]
    return out.reset_index(drop=True)
