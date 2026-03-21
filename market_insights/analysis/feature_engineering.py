from __future__ import annotations

import pandas as pd


def compute_market_context(df: pd.DataFrame) -> dict:
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    price = float(latest["close"])
    high = float(latest["high"])
    low = float(latest["low"])
    open_ = float(latest["open"])
    volume = float(latest["volume"])
    prev_close = float(prev["close"])

    day_change_pct = ((price / prev_close) - 1.0) * 100 if prev_close else 0.0
    intraday_range_pct = ((high - low) / price) * 100 if price else 0.0
    body_pct = ((price - open_) / open_) * 100 if open_ else 0.0
    volume_avg_20 = float(df["volume"].tail(20).mean()) if len(df) else volume
    volume_ratio = volume / volume_avg_20 if volume_avg_20 else 1.0
    near_20d_high = float(df["high"].tail(20).max())
    near_20d_low = float(df["low"].tail(20).min())
    pct_from_20d_high = ((price / near_20d_high) - 1.0) * 100 if near_20d_high else 0.0
    pct_from_20d_low = ((price / near_20d_low) - 1.0) * 100 if near_20d_low else 0.0

    return {
        "current_price": round(price, 2),
        "open": round(open_, 2),
        "high": round(high, 2),
        "low": round(low, 2),
        "volume": round(volume, 2),
        "day_change_pct": round(day_change_pct, 2),
        "intraday_range_pct": round(intraday_range_pct, 2),
        "body_pct": round(body_pct, 2),
        "volume_ratio": round(volume_ratio, 2),
        "high_20d": round(near_20d_high, 2),
        "low_20d": round(near_20d_low, 2),
        "pct_from_20d_high": round(pct_from_20d_high, 2),
        "pct_from_20d_low": round(pct_from_20d_low, 2),
    }
