"""Tests for macro connectors."""

from market_insights.connectors.open_data.macro import SampleMacroConnector


def test_sample_macro_has_sections():
    data = SampleMacroConnector().fetch()
    assert "rates" in data
    assert "inflation" in data
    assert "growth" in data
    assert "labor" in data
    assert "sentiment" in data


def test_sample_macro_rates():
    data = SampleMacroConnector().fetch()
    assert data["rates"]["fed_funds"] > 0
    assert data["rates"]["treasury_10y"] > 0
