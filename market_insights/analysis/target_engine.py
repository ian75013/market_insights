from __future__ import annotations

import pandas as pd


def compute_price_levels(df: pd.DataFrame) -> dict:
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    high = float(latest["high"])
    low = float(latest["low"])
    close = float(latest["close"])

    pivot = (high + low + close) / 3.0
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)

    recent_highs = sorted(set(float(x) for x in df["high"].tail(40).tolist()))
    recent_lows = sorted(set(float(x) for x in df["low"].tail(40).tolist()))
    next_res = next((x for x in recent_highs if x > close), r1)
    second_res = next((x for x in recent_highs if x > next_res), r2)
    next_sup_candidates = [x for x in recent_lows if x < close]
    next_sup = next_sup_candidates[-1] if next_sup_candidates else s1

    return {
        "pivot": round(pivot, 2),
        "support": round(min(next_sup, s1), 2),
        "support_2": round(s2, 2),
        "resistance": round(max(next_res, r1), 2),
        "resistance_2": round(max(second_res, r2), 2),
        "invalidation": round(min(next_sup, s1), 2),
        "target_1": round(max(next_res, r1), 2),
        "target_2": round(max(second_res, r2), 2),
    }
