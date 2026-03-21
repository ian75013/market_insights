"""Tests for the TTL cache layer."""

import time

from market_insights.core.cache import CacheStore, ttl_cache


def test_cache_store_set_and_get():
    store = CacheStore()
    store.set("k1", "hello", ttl=10)
    assert store.get("k1") == "hello"


def test_cache_store_expiry():
    store = CacheStore()
    store.set("k2", "world", ttl=0)
    time.sleep(0.05)
    assert store.get("k2") is None


def test_cache_store_invalidate_prefix():
    store = CacheStore()
    store.set("prices:AAPL", 1, ttl=60)
    store.set("prices:MSFT", 2, ttl=60)
    store.set("macro:fed", 3, ttl=60)
    cleared = store.invalidate("prices:")
    assert cleared == 2
    assert store.get("macro:fed") == 3


def test_cache_store_stats():
    store = CacheStore()
    store.set("a", 1, ttl=60)
    store.set("b", 2, ttl=0)
    time.sleep(0.05)
    stats = store.stats()
    assert stats["total_keys"] == 2
    assert stats["alive_keys"] == 1


def test_ttl_cache_decorator():
    call_count = 0

    @ttl_cache(seconds=60, prefix="test_dec")
    def compute(x):
        nonlocal call_count
        call_count += 1
        return x * 2

    assert compute(5) == 10
    assert compute(5) == 10  # cached
    assert call_count == 1

    compute.cache_invalidate()
    assert compute(5) == 10  # recomputed
    assert call_count == 2
