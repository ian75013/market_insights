"""Tests for the price provider router."""

from market_insights.etl.extractors.price_provider import PriceProviderRouter


def test_available_providers_includes_sample():
    router = PriceProviderRouter(use_network=False)
    providers = router.available_providers()
    names = [p["name"] for p in providers]
    assert "sample" in names


def test_sample_provider_returns_data():
    router = PriceProviderRouter(use_network=False)
    df = router.fetch_prices("AAPL", provider="sample")
    assert not df.empty
    assert df.iloc[0]["ticker"] == "AAPL"


def test_sample_provider_multiple_tickers():
    router = PriceProviderRouter(use_network=False)
    for ticker in ["MSFT", "NVDA", "GOOGL", "JPM"]:
        df = router.fetch_prices(ticker, provider="sample")
        assert not df.empty
        assert df.iloc[0]["ticker"] == ticker


def test_unknown_provider_raises():
    router = PriceProviderRouter(use_network=False)
    try:
        router.fetch_prices("AAPL", provider="nonexistent")
        assert False, "Should have raised"
    except ValueError:
        pass
