"""Multi-source news connector with RSS, Alpha Vantage, and sample fallback.

RSS feeds used (all free, no key):
- Google News RSS (filtered by ticker)
- Yahoo Finance RSS
- Seeking Alpha RSS (if available)
"""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from market_insights.connectors.open_data.base import BaseHTTPConnector
from market_insights.core.cache import ttl_cache
from market_insights.core.config import settings

logger = logging.getLogger(__name__)

SAMPLE_NEWS = Path(__file__).resolve().parents[2] / "data" / "sample" / "news.json"


class SampleNewsConnector:
    provider_name = "sample_news"

    def fetch(self, ticker: str) -> list[dict]:
        data = json.loads(SAMPLE_NEWS.read_text(encoding="utf-8"))
        return data.get(ticker.upper(), [])


class RSSNewsConnector(BaseHTTPConnector):
    """Multi-feed RSS news aggregator."""

    provider_name = "rss"

    RSS_FEEDS = [
        "https://news.google.com/rss/search?q={ticker}%20stock&hl=en-US&gl=US&ceid=US:en",
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(cache_ttl=settings.cache_ttl_news, **kwargs)

    @ttl_cache(seconds=settings.cache_ttl_news, prefix="rss_news")
    def fetch(self, ticker: str, max_items: int = 10) -> list[dict]:
        if not self.use_network:
            return SampleNewsConnector().fetch(ticker)

        all_items: list[dict] = []
        for feed_url_template in self.RSS_FEEDS:
            try:
                url = feed_url_template.format(ticker=ticker.upper())
                xml_text = self.get_text(
                    url, cache_key=f"rss:{ticker}:{feed_url_template[:30]}"
                )
                items = self._parse_rss(xml_text, max_items=max_items)
                all_items.extend(items)
            except Exception as exc:
                logger.warning("RSS feed failed for %s: %s", ticker, exc)

        if not all_items:
            logger.info("No RSS items found for %s, falling back to sample", ticker)
            return SampleNewsConnector().fetch(ticker)

        # Deduplicate by title
        seen_titles: set[str] = set()
        unique: list[dict] = []
        for item in all_items:
            title_key = item["title"].lower().strip()[:60]
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique.append(item)

        return unique[:max_items]

    @staticmethod
    def _parse_rss(xml_text: str, max_items: int = 10) -> list[dict]:
        root = ET.fromstring(xml_text)
        items: list[dict] = []
        for item_el in root.findall(".//item")[:max_items]:
            items.append(
                {
                    "title": item_el.findtext("title", default=""),
                    "link": item_el.findtext("link", default=""),
                    "published_at": item_el.findtext("pubDate", default=""),
                    "content": (item_el.findtext("description", default="") or "")[
                        :400
                    ],
                    "source": item_el.findtext("source", default="RSS"),
                }
            )
        return items


class MultiNewsConnector:
    """Cascading news connector: Alpha Vantage → RSS → Sample."""

    provider_name = "multi_news"

    def fetch(self, ticker: str, max_items: int = 10) -> list[dict]:
        # 1. Alpha Vantage news sentiment
        try:
            from market_insights.connectors.open_data.alpha_vantage import (
                AlphaVantageNewsConnector,
            )

            conn = AlphaVantageNewsConnector()
            if conn.available():
                items = conn.fetch(ticker, limit=max_items)
                if items:
                    logger.info(
                        "News for %s resolved via Alpha Vantage (%d items)",
                        ticker,
                        len(items),
                    )
                    return items
        except Exception as exc:
            logger.debug("Alpha Vantage news failed for %s: %s", ticker, exc)

        # 2. RSS feeds
        try:
            conn = RSSNewsConnector(use_network=settings.use_network)
            items = conn.fetch(ticker, max_items=max_items)
            if items:
                return items
        except Exception as exc:
            logger.debug("RSS news failed for %s: %s", ticker, exc)

        # 3. Sample
        return SampleNewsConnector().fetch(ticker)
