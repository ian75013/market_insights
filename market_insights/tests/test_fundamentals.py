"""Tests for fundamentals connectors."""

from market_insights.connectors.open_data.fundamentals import (
    SampleFundamentalsConnector,
)


def test_sample_fundamentals_all_tickers():
    conn = SampleFundamentalsConnector()
    for ticker in [
        "AAPL",
        "MSFT",
        "NVDA",
        "GOOGL",
        "AMZN",
        "META",
        "TSLA",
        "JPM",
        "JNJ",
        "BTC",
    ]:
        data = conn.fetch(ticker)
        assert "revenue_growth" in data
        assert "debt_to_equity" in data
        assert "pe" in data


def test_sample_fundamentals_unknown_ticker_raises():
    conn = SampleFundamentalsConnector()
    try:
        conn.fetch("ZZZZZ")
        assert False, "Should have raised"
    except ValueError:
        pass
