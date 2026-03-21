"""Multi-source news connector — HTML nettoyé + résumé extractif."""
from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from market_insights.connectors.open_data.base import BaseHTTPConnector
from market_insights.core.cache import ttl_cache
from market_insights.core.config import settings
from market_insights.nlp.summarizer import strip_html, summarize

logger = logging.getLogger(__name__)
SAMPLE_NEWS = Path(__file__).resolve().parents[2] / "data" / "sample" / "news.json"


class SampleNewsConnector:
    provider_name = "sample_news"
    def fetch(self, ticker: str) -> list[dict]:
        data = json.loads(SAMPLE_NEWS.read_text(encoding="utf-8"))
        return data.get(ticker.upper(), [])


class RSSNewsConnector(BaseHTTPConnector):
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
        for tpl in self.RSS_FEEDS:
            try:
                url = tpl.format(ticker=ticker.upper())
                xml_text = self.get_text(url, cache_key=f"rss:{ticker}:{tpl[:30]}")
                all_items.extend(self._parse_rss(xml_text, ticker, max_items))
            except Exception as exc:
                logger.warning("RSS feed failed for %s: %s", ticker, exc)
        if not all_items:
            return SampleNewsConnector().fetch(ticker)
        seen: set[str] = set()
        unique: list[dict] = []
        for item in all_items:
            k = item["title"].lower().strip()[:60]
            if k not in seen:
                seen.add(k)
                unique.append(item)
        return unique[:max_items]

    @staticmethod
    def _parse_rss(xml_text: str, ticker: str, max_items: int = 10) -> list[dict]:
        root = ET.fromstring(xml_text)
        items: list[dict] = []
        for el in root.findall(".//item")[:max_items]:
            raw_title = el.findtext("title", default="")
            raw_desc = el.findtext("description", default="")
            raw_source = el.findtext("source", default="")
            raw_link = el.findtext("link", default="")
            # Clean HTML
            clean_title = strip_html(raw_title)
            clean_desc = strip_html(raw_desc)
            # Extract source from title "... - Forbes" pattern
            source = raw_source
            if not source and " - " in clean_title:
                source = clean_title.rsplit(" - ", 1)[-1].strip()
                clean_title = clean_title.rsplit(" - ", 1)[0].strip()
            # Summarize description
            summary = summarize(clean_desc, max_sentences=2, max_chars=250) if clean_desc else ""
            items.append({
                "title": clean_title,
                "link": raw_link,
                "published_at": el.findtext("pubDate", default=""),
                "content": summary,
                "source": source or "RSS",
            })
        return items


class MultiNewsConnector:
    provider_name = "multi_news"
    def fetch(self, ticker: str, max_items: int = 10) -> list[dict]:
        try:
            from market_insights.connectors.open_data.alpha_vantage import AlphaVantageNewsConnector
            conn = AlphaVantageNewsConnector()
            if conn.available():
                items = conn.fetch(ticker, limit=max_items)
                if items:
                    return items
        except Exception:
            pass
        try:
            conn = RSSNewsConnector(use_network=settings.use_network)
            items = conn.fetch(ticker, max_items=max_items)
            if items:
                return items
        except Exception:
            pass
        return SampleNewsConnector().fetch(ticker)
