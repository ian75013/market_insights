from market_insights.connectors.open_data.prices import SamplePriceConnector
from market_insights.connectors.ibkr.historical import IBHistoricalFetcher


def test_sample_price_connector_returns_rows():
    df = SamplePriceConnector().fetch("AAPL")
    assert not df.empty
    assert set(["ticker", "date", "open", "high", "low", "close", "volume"]).issubset(
        df.columns
    )


def test_ib_fetcher_falls_back_to_sample():
    df = IBHistoricalFetcher().fetch_prices("AAPL")
    assert not df.empty
    assert df.iloc[0]["ticker"] == "AAPL"
