"""CoinGecko connector — 100% free, no API key required.

Provides:
- crypto prices (OHLCV via market_chart)
- coin info (market cap, volume, description)
- trending coins
- global market data

Docs: https://docs.coingecko.com/v3.0.1/reference/introduction
Rate limit: ~10-30 req/min on free tier.
"""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from market_insights.connectors.open_data.base import BaseHTTPConnector
from market_insights.core.cache import ttl_cache
from market_insights.core.config import settings

logger = logging.getLogger(__name__)

CG_BASE = "https://api.coingecko.com/api/v3"

# Common ticker-to-coingecko-id mapping
TICKER_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "ADA": "cardano", "DOGE": "dogecoin", "DOT": "polkadot",
    "AVAX": "avalanche-2", "MATIC": "matic-network", "LINK": "chainlink",
    "UNI": "uniswap", "XRP": "ripple", "BNB": "binancecoin",
    "ATOM": "cosmos", "LTC": "litecoin", "NEAR": "near",
}


class CoinGeckoPriceConnector(BaseHTTPConnector):
    """Fetch crypto OHLC prices from CoinGecko."""

    provider_name = "coingecko"

    def __init__(self, **kwargs) -> None:
        super().__init__(cache_ttl=settings.cache_ttl_prices, **kwargs)

    def available(self) -> bool:
        return self.use_network

    @ttl_cache(seconds=settings.cache_ttl_prices, prefix="cg_prices")
    def fetch(self, ticker: str, days: int = 180) -> pd.DataFrame:
        if not self.use_network:
            raise ConnectionError("CoinGecko: network disabled")

        coin_id = TICKER_MAP.get(ticker.upper(), ticker.lower())
        url = f"{CG_BASE}/coins/{coin_id}/ohlc?vs_currency=usd&days={days}"
        logger.info("CoinGecko: fetching %s OHLC (%d days)", coin_id, days)

        data = self.get_json(url, cache_key=f"cg_ohlc:{coin_id}:{days}")

        if not data or not isinstance(data, list):
            raise ValueError(f"CoinGecko returned no OHLC for {ticker}")

        rows = []
        for ts, o, h, l, c in data:
            rows.append({
                "ticker": ticker.upper(),
                "date": datetime.utcfromtimestamp(ts / 1000),
                "open": o, "high": h, "low": l, "close": c,
                "volume": 0,  # OHLC endpoint doesn't include volume
            })
        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        return df


class CoinGeckoInfoConnector(BaseHTTPConnector):
    """Fetch coin info from CoinGecko."""

    provider_name = "coingecko_info"

    def __init__(self, **kwargs) -> None:
        super().__init__(cache_ttl=3600, **kwargs)

    def available(self) -> bool:
        return self.use_network

    @ttl_cache(seconds=3600, prefix="cg_info")
    def fetch(self, ticker: str) -> dict:
        if not self.use_network:
            raise ConnectionError("CoinGecko: network disabled")

        coin_id = TICKER_MAP.get(ticker.upper(), ticker.lower())
        url = f"{CG_BASE}/coins/{coin_id}?localization=false&tickers=false&community_data=false&developer_data=false"
        logger.info("CoinGecko: fetching %s info", coin_id)

        data = self.get_json(url, cache_key=f"cg_info:{coin_id}")

        md = data.get("market_data", {})
        return {
            "ticker": ticker.upper(),
            "name": data.get("name", ""),
            "symbol": data.get("symbol", ""),
            "market_cap": md.get("market_cap", {}).get("usd", 0),
            "current_price": md.get("current_price", {}).get("usd", 0),
            "total_volume_24h": md.get("total_volume", {}).get("usd", 0),
            "price_change_24h_pct": md.get("price_change_percentage_24h", 0),
            "price_change_7d_pct": md.get("price_change_percentage_7d", 0),
            "price_change_30d_pct": md.get("price_change_percentage_30d", 0),
            "ath": md.get("ath", {}).get("usd", 0),
            "ath_date": md.get("ath_date", {}).get("usd", ""),
            "circulating_supply": md.get("circulating_supply", 0),
            "total_supply": md.get("total_supply", 0),
            "description": (data.get("description", {}).get("en", "") or "")[:500],
            "categories": data.get("categories", []),
        }


class CoinGeckoGlobalConnector(BaseHTTPConnector):
    """Fetch global crypto market data."""

    provider_name = "coingecko_global"

    def __init__(self, **kwargs) -> None:
        super().__init__(cache_ttl=settings.cache_ttl_macro, **kwargs)

    @ttl_cache(seconds=settings.cache_ttl_macro, prefix="cg_global")
    def fetch(self) -> dict:
        if not self.use_network:
            raise ConnectionError("CoinGecko: network disabled")

        data = self.get_json(f"{CG_BASE}/global", cache_key="cg_global")
        gd = data.get("data", {})
        return {
            "total_market_cap_usd": gd.get("total_market_cap", {}).get("usd", 0),
            "total_volume_24h_usd": gd.get("total_volume", {}).get("usd", 0),
            "btc_dominance": gd.get("market_cap_percentage", {}).get("btc", 0),
            "eth_dominance": gd.get("market_cap_percentage", {}).get("eth", 0),
            "active_cryptocurrencies": gd.get("active_cryptocurrencies", 0),
            "market_cap_change_24h_pct": gd.get("market_cap_change_percentage_24h_usd", 0),
        }
