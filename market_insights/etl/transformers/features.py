import numpy as np
import pandas as pd


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().sort_values("date")
    out["return_1d"] = out["close"].pct_change().fillna(0.0)
    out["sma_5"] = out["close"].rolling(5, min_periods=1).mean()
    out["sma_20"] = out["close"].rolling(20, min_periods=1).mean()
    out["momentum_20"] = out["close"] / out["close"].shift(20) - 1
    out["volatility_20"] = out["return_1d"].rolling(20, min_periods=2).std().fillna(0.0)

    delta = out["close"].diff().fillna(0.0)
    gain = delta.clip(lower=0).rolling(14, min_periods=1).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=1).mean().replace(0, np.nan)
    rs = gain / loss
    out["rsi_14"] = 100 - (100 / (1 + rs))
    out["rsi_14"] = out["rsi_14"].fillna(50.0)

    out["drawdown"] = out["close"] / out["close"].cummax() - 1
    out["trend_signal"] = (out["sma_5"] > out["sma_20"]).astype(int)
    return out.fillna(0.0)
