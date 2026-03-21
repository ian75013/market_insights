"""Base HTTP connector with retry, rate-limit awareness, and caching hooks."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from market_insights.core.cache import cache_store
from market_insights.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    provider: str
    payload: list[dict]
    used_network: bool
    fallback_used: bool = False
    cached: bool = False


class BaseHTTPConnector:
    provider_name = "base"

    def __init__(
        self,
        use_network: bool | None = None,
        timeout: float = 20.0,
        max_retries: int = 2,
        cache_ttl: int = 300,
    ) -> None:
        self.use_network = settings.use_network if use_network is None else use_network
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache_ttl = cache_ttl

    # ── HTTP helpers ───────────────────────────────────────────────

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": settings.sec_user_agent},
        )

    def get_json(self, url: str, *, cache_key: str = "") -> dict | list:
        if cache_key:
            cached = cache_store.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit: %s", cache_key)
                return cached

        data = self._request_with_retry(url, parse="json")

        if cache_key:
            cache_store.set(cache_key, data, ttl=self.cache_ttl)
        return data

    def get_text(self, url: str, *, cache_key: str = "") -> str:
        if cache_key:
            cached = cache_store.get(cache_key)
            if cached is not None:
                return cached

        data = self._request_with_retry(url, parse="text")

        if cache_key:
            cache_store.set(cache_key, data, ttl=self.cache_ttl)
        return data

    def get_csv_text(self, url: str, *, cache_key: str = "") -> str:
        return self.get_text(url, cache_key=cache_key)

    # ── Retry logic ────────────────────────────────────────────────

    def _request_with_retry(self, url: str, parse: str = "json") -> dict | list | str:
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with self._client() as client:
                    resp = client.get(url)
                    if resp.status_code == 429:
                        wait = int(resp.headers.get("Retry-After", 5))
                        logger.warning("Rate-limited by %s, waiting %ds (attempt %d)", url[:60], wait, attempt)
                        time.sleep(min(wait, 30))
                        continue
                    resp.raise_for_status()
                    return resp.json() if parse == "json" else resp.text
            except Exception as exc:
                last_exc = exc
                logger.warning("HTTP error on %s (attempt %d): %s", url[:60], attempt, exc)
                if attempt < self.max_retries:
                    time.sleep(1.5 * attempt)
        raise ConnectionError(f"Failed after {self.max_retries} attempts: {last_exc}") from last_exc
