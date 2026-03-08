from __future__ import annotations

import pandas as pd

from market_insights.connectors.ibkr.historical import IBHistoricalFetcher
from market_insights.connectors.open_data.prices import SamplePriceConnector, StooqPriceConnector
from market_insights.core.config import settings


class PriceProviderRouter:
    def __init__(self, use_network: bool | None = None) -> None:
        self.use_network = settings.use_network if use_network is None else use_network

    def fetch_prices(self, ticker: str, provider: str | None = None) -> pd.DataFrame:
        provider = (provider or settings.default_price_provider).lower()
        if provider == "sample":
            return SamplePriceConnector().fetch(ticker)
        if provider == "stooq":
            return StooqPriceConnector(use_network=self.use_network).fetch(ticker)
        if provider == "ibkr":
            return IBHistoricalFetcher().fetch_prices(ticker)
        raise ValueError(f"Unknown provider={provider}")
