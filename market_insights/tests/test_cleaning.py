import pandas as pd

from market_insights.etl.transformers.cleaning import clean_market_data


def test_clean_market_data_removes_duplicates_and_fills():
    df = pd.DataFrame([
        {"ticker": "AAPL", "date": "2025-01-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10},
        {"ticker": "AAPL", "date": "2025-01-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10},
        {"ticker": "AAPL", "date": "2025-01-02", "open": None, "high": None, "low": None, "close": 2.0, "volume": 20},
    ])
    out = clean_market_data(df)
    assert len(out) == 2
    assert out.iloc[1]["open"] == 2.0
