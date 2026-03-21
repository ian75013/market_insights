"""In-memory TTL cache to avoid hammering free-tier APIs.

Usage:
    from market_insights.core.cache import ttl_cache

    @ttl_cache(seconds=900)
    def expensive_api_call(ticker: str) -> dict:
        ...

Or use the global store directly:
    from market_insights.core.cache import cache_store
    cache_store.get("key")
    cache_store.set("key", value, ttl=600)
"""

from __future__ import annotations

import functools
import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class CacheStore:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self) -> None:
        self._data: dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                del self._data[key]
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        with self._lock:
            self._data[key] = _CacheEntry(value=value, expires_at=time.monotonic() + ttl)

    def invalidate(self, prefix: str = "") -> int:
        with self._lock:
            keys = [k for k in self._data if k.startswith(prefix)]
            for k in keys:
                del self._data[k]
            return len(keys)

    def stats(self) -> dict:
        with self._lock:
            now = time.monotonic()
            total = len(self._data)
            alive = sum(1 for e in self._data.values() if now <= e.expires_at)
            return {"total_keys": total, "alive_keys": alive, "expired_keys": total - alive}


cache_store = CacheStore()


def ttl_cache(seconds: int = 300, prefix: str = ""):
    """Decorator: caches return value keyed on function name + args."""

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            raw = json.dumps({"a": [str(a) for a in args], "k": {str(k): str(v) for k, v in sorted(kwargs.items())}}, sort_keys=True)
            key = f"{prefix or fn.__qualname__}:{hashlib.md5(raw.encode()).hexdigest()}"
            cached = cache_store.get(key)
            if cached is not None:
                return cached
            result = fn(*args, **kwargs)
            cache_store.set(key, result, ttl=seconds)
            return result

        wrapper.cache_invalidate = lambda: cache_store.invalidate(prefix or fn.__qualname__)
        return wrapper

    return decorator
