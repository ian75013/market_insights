"""Tests for candlestick annotation engine."""

import pandas as pd
from market_insights.analysis.candlestick_engine import annotate_candlesticks


def _sample_df():
    rows = []
    price = 100.0
    for i in range(30):
        # Create some interesting patterns
        if i == 10:  # gap up
            price += 5
        if i == 20:  # gap down
            price -= 3
        rows.append(
            {
                "ticker": "TEST",
                "date": pd.Timestamp("2025-01-01") + pd.Timedelta(days=i),
                "open": price - 0.5 + (0.8 if i % 5 == 0 else 0),
                "high": price + 1.5,
                "low": price - 1.0 - (0.5 if i == 15 else 0),
                "close": price + 0.3 * (1 if i % 2 == 0 else -1),
                "volume": 1000 + i * 10 + (3000 if i == 25 else 0),
            }
        )
        price += 0.5
    return pd.DataFrame(rows)


def test_annotate_returns_bars():
    df = _sample_df()
    bars = annotate_candlesticks(df)
    assert len(bars) == 30
    assert "date" in bars[0]
    assert "open" in bars[0]
    assert "signals" in bars[0]
    assert isinstance(bars[0]["signals"], list)


def test_annotate_detects_signals():
    df = _sample_df()
    bars = annotate_candlesticks(df)
    all_signals = []
    for b in bars:
        all_signals.extend(b["signals"])
    # Should detect at least some signals
    types = {s["type"] for s in all_signals}
    assert len(types) >= 1
    # Each signal has required keys
    for s in all_signals:
        assert "type" in s
        assert "label" in s
        assert "severity" in s
