"""Multi-provider price router with auto-fallback cascade.

Supported providers:
- sample   : offline bundled CSV
- stooq    : Stooq.com free EOD (no key)
- yahoo    : Yahoo Finance via yfinance (no key)
- alpha    : Alpha Vantage (free key)
- coingecko: CoinGecko crypto (no key)  ← default for crypto tickers
- ibkr     : Interactive Brokers TWS/Gateway
- auto     : crypto → coingecko first; stocks → yahoo → stooq → alpha → sample
"""

from __future__ import annotations

import logging

import pandas as pd

from market_insights.connectors.ibkr.historical import IBHistoricalFetcher
from market_insights.connectors.open_data.coingecko import (
    TICKER_MAP as CG_TICKER_MAP,
    is_crypto_ticker as _is_crypto,
    normalize_crypto_ticker as _normalize_crypto_ticker,
)
from market_insights.connectors.open_data.prices import (
    SamplePriceConnector,
    StooqPriceConnector,
)
from market_insights.core.config import settings

logger = logging.getLogger(__name__)

# Re-export coingecko's suffixes for canonical_ticker / crypto_aliases
_YAHOO_CRYPTO_SUFFIXES = {"-USD", "-EUR", "-GBP", "-JPY", "-BTC"}


def is_crypto(ticker: str) -> bool:
    """Detect whether *ticker* refers to a cryptocurrency."""
    return _is_crypto(ticker)


def normalize_crypto_ticker(ticker: str) -> str:
    """Strip Yahoo-style suffix: BTC-USD → BTC."""
    return _normalize_crypto_ticker(ticker)


def canonical_ticker(ticker: str) -> str:
    """Return the canonical DB ticker.

    For crypto: always the base symbol (BTC, ETH …) — never BTC-USD.
    For stocks: unchanged, uppercased.
    """
    t = ticker.upper()
    if _is_crypto(t):
        return _normalize_crypto_ticker(t)
    return t


def crypto_aliases(ticker: str) -> list[str]:
    """Return all known DB aliases for a crypto ticker.

    >>> crypto_aliases("BTC")
    ["BTC", "BTC-USD", "BTC-EUR", "BTC-GBP"]
    """
    base = _normalize_crypto_ticker(ticker)
    if base not in CG_TICKER_MAP:
        return [ticker.upper()]
    return [base] + [f"{base}{s}" for s in _YAHOO_CRYPTO_SUFFIXES]


class PriceProviderRouter:
    def __init__(self, use_network: bool | None = None) -> None:
        self.use_network = settings.use_network if use_network is None else use_network

    def fetch_prices(self, ticker: str, provider: str | None = None) -> pd.DataFrame:
        provider = (provider or settings.default_price_provider).lower()

        if provider == "auto":
            return self._auto_resolve(ticker)

        # ── Crypto guard: redirect non-CoinGecko providers to CoinGecko ──
        # Yahoo, Stooq, Alpha Vantage return wrong data for bare crypto
        # tickers like "BTC" (e.g. Grayscale trust at $31 instead of Bitcoin).
        if _is_crypto(ticker) and provider in ("yahoo", "stooq", "alpha", "alpha_vantage"):
            logger.info(
                "Crypto ticker %s detected — redirecting from %s to coingecko",
                ticker, provider,
            )
            return self._from_coingecko(ticker)

        dispatch = {
            "sample": self._from_sample,
            "stooq": self._from_stooq,
            "yahoo": self._from_yahoo,
            "alpha": self._from_alpha_vantage,
            "alpha_vantage": self._from_alpha_vantage,
            "coingecko": self._from_coingecko,
            "ibkr": self._from_ibkr,
        }
        fetcher = dispatch.get(provider)
        if fetcher is None:
            raise ValueError(
                f"Unknown provider={provider}. Available: {', '.join(dispatch.keys())}"
            )
        return fetcher(ticker)

    def available_providers(self) -> list[dict]:
        """List all providers and their availability status."""
        providers = [
            {
                "name": "sample",
                "available": True,
                "needs_key": False,
                "needs_network": False,
            },
            {
                "name": "stooq",
                "available": self.use_network,
                "needs_key": False,
                "needs_network": True,
            },
        ]
        # Yahoo
        try:
            from market_insights.connectors.open_data.yahoo import (
                YFinancePriceConnector,
            )

            providers.append(
                {
                    "name": "yahoo",
                    "available": YFinancePriceConnector.available()
                    and self.use_network,
                    "needs_key": False,
                    "needs_network": True,
                }
            )
        except Exception:
            providers.append(
                {
                    "name": "yahoo",
                    "available": False,
                    "needs_key": False,
                    "needs_network": True,
                }
            )

        # Alpha Vantage
        providers.append(
            {
                "name": "alpha_vantage",
                "available": bool(settings.alpha_vantage_api_key) and self.use_network,
                "needs_key": True,
                "needs_network": True,
            }
        )
        # CoinGecko
        providers.append(
            {
                "name": "coingecko",
                "available": self.use_network,
                "needs_key": False,
                "needs_network": True,
            }
        )
        # IBKR
        providers.append(
            {
                "name": "ibkr",
                "available": False,  # needs TWS running
                "needs_key": False,
                "needs_network": True,
            }
        )
        return providers

    # ── Individual provider methods ────────────────────────────────

    def _from_sample(self, ticker: str) -> pd.DataFrame:
        return SamplePriceConnector().fetch(ticker)

    def _from_stooq(self, ticker: str) -> pd.DataFrame:
        return StooqPriceConnector(use_network=self.use_network).fetch(ticker)

    def _from_yahoo(self, ticker: str) -> pd.DataFrame:
        from market_insights.connectors.open_data.yahoo import YFinancePriceConnector

        return YFinancePriceConnector().fetch(ticker)

    def _from_alpha_vantage(self, ticker: str) -> pd.DataFrame:
        from market_insights.connectors.open_data.alpha_vantage import (
            AlphaVantagePriceConnector,
        )

        return AlphaVantagePriceConnector().fetch(ticker)

    def _from_coingecko(self, ticker: str) -> pd.DataFrame:
        from market_insights.connectors.open_data.coingecko import (
            CoinGeckoPriceConnector,
        )

        # Normalize Yahoo-style pairs: BTC-USD → BTC
        normalized = _normalize_crypto_ticker(ticker)
        df = CoinGeckoPriceConnector(use_network=self.use_network).fetch(normalized)
        # Always use canonical ticker so BTC and BTC-USD map to same DB rows
        if not df.empty:
            df["ticker"] = canonical_ticker(ticker)
        return df

    def _from_ibkr(self, ticker: str) -> pd.DataFrame:
        return IBHistoricalFetcher().fetch_prices(ticker)

    # ── Auto resolution ────────────────────────────────────────────

    def _auto_resolve(self, ticker: str) -> pd.DataFrame:
        """Try providers in priority order, return first success.

        For crypto tickers the cascade is:
            coingecko → sample
        For stocks:
            yahoo → stooq → alpha_vantage → sample
        """
        crypto = _is_crypto(ticker)
        chain = []

        if self.use_network:
            if crypto:
                # CoinGecko first (and only real source) for crypto
                chain.append(("coingecko", self._from_coingecko))
            else:
                chain.append(("yahoo", self._from_yahoo))
                chain.append(("stooq", self._from_stooq))
                if settings.alpha_vantage_api_key:
                    chain.append(("alpha_vantage", self._from_alpha_vantage))

        chain.append(("sample", self._from_sample))

        errors: list[str] = []
        for name, fetcher in chain:
            try:
                df = fetcher(ticker)
                if df is not None and not df.empty:
                    logger.info("Auto-resolved prices for %s via %s", ticker, name)
                    return df
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                logger.debug("Provider %s failed for %s: %s", name, ticker, exc)

        raise ValueError(
            f"No price data for {ticker} from any provider. Errors: {'; '.join(errors)}"
        )
