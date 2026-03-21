import pandas as pd

from market_insights.ml.fair_value import BaselineFairValueModel


def test_baseline_fair_value_predicts_positive_value():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=3),
            "close": [100, 101, 102],
            "momentum_20": [0.0, 0.0, 0.05],
            "volatility_20": [0.0, 0.01, 0.02],
            "trend_signal": [0, 1, 1],
            "rsi_14": [50, 55, 60],
        }
    )
    result = BaselineFairValueModel().predict(df)
    assert result.fair_value > 0
    assert 0 <= result.confidence <= 1
