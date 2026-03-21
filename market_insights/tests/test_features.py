import pandas as pd

from market_insights.etl.transformers.features import compute_features


def test_compute_features_adds_expected_columns():
    df = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 5,
            "date": pd.date_range("2025-01-01", periods=5),
            "open": [1, 2, 3, 4, 5],
            "high": [1, 2, 3, 4, 5],
            "low": [1, 2, 3, 4, 5],
            "close": [1, 2, 3, 4, 5],
            "volume": [10, 11, 12, 13, 14],
        }
    )
    out = compute_features(df)
    assert "rsi_14" in out.columns
    assert "volatility_20" in out.columns
    assert "trend_signal" in out.columns
