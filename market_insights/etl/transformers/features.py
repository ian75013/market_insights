from __future__ import annotations

import numpy as np
import pandas as pd


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.rolling(period, min_periods=1).mean()
    ma_down = down.rolling(period, min_periods=1).mean().replace(0, np.nan)
    rs = ma_up / ma_down
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().sort_values("date").reset_index(drop=True)
    out["return_1d"] = out["close"].pct_change().fillna(0.0)
    out["momentum_20"] = out["close"].pct_change(20).fillna(0.0)
    out["sma_20"] = out["close"].rolling(20, min_periods=1).mean()
    out["sma_50"] = out["close"].rolling(50, min_periods=1).mean()
    out["volatility_20"] = out["return_1d"].rolling(20, min_periods=2).std().fillna(0.0)
    out["rsi_14"] = _rsi(out["close"], 14)
    out["trend_signal"] = (out["sma_20"] >= out["sma_50"]).astype(int)
    out["cummax_close"] = out["close"].cummax()
    out["drawdown"] = (out["close"] / out["cummax_close"] - 1.0).fillna(0.0)
    return out
