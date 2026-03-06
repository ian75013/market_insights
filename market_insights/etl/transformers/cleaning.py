import pandas as pd


REQUIRED_COLUMNS = ["ticker", "date", "open", "high", "low", "close", "volume"]


def clean_market_data(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    out = df.copy()
    out = out.drop_duplicates(subset=["ticker", "date"]).sort_values("date")
    out["volume"] = out["volume"].clip(lower=0)
    for col in ["open", "high", "low", "close"]:
        out[col] = out[col].astype(float)
    out["close"] = out["close"].ffill().bfill()
    out["open"] = out["open"].fillna(out["close"])
    out["high"] = out["high"].fillna(out[["open", "close"]].max(axis=1))
    out["low"] = out["low"].fillna(out[["open", "close"]].min(axis=1))
    return out.reset_index(drop=True)
