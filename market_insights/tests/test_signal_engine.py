import pandas as pd

from market_insights.analysis.feature_engineering import compute_market_context
from market_insights.analysis.signal_detection import detect_signals
from market_insights.analysis.target_engine import compute_price_levels
from market_insights.etl.transformers.features import compute_features


def _sample_df() -> pd.DataFrame:
    rows = []
    price = 100.0
    for i in range(30):
        price += 1.0
        rows.append(
            {
                "date": pd.Timestamp("2025-01-01") + pd.Timedelta(days=i),
                "open": price - 0.5,
                "high": price + 1.0,
                "low": price - 1.0,
                "close": price,
                "volume": 1000 + i * 10,
            }
        )
    return compute_features(pd.DataFrame(rows))


def test_market_context_and_levels():
    df = _sample_df()
    ctx = compute_market_context(df)
    levels = compute_price_levels(df)
    assert ctx["current_price"] > 0
    assert levels["target_2"] >= levels["target_1"]
    assert levels["resistance"] >= levels["support"]


def test_signal_detection():
    df = _sample_df()
    signals = detect_signals(df)
    assert "patterns" in signals
    assert "candles" in signals
    assert "flags" in signals
