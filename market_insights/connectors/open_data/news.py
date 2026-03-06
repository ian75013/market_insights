from __future__ import annotations

from pathlib import Path
import json
import xml.etree.ElementTree as ET

from market_insights.connectors.open_data.base import BaseHTTPConnector


SAMPLE_NEWS = Path(__file__).resolve().parents[2] / "data" / "sample" / "news.json"


class SampleNewsConnector:
    provider_name = "sample_news"

    def fetch(self, ticker: str) -> list[dict]:
        data = json.loads(SAMPLE_NEWS.read_text(encoding="utf-8"))
        return data.get(ticker.upper(), [])


class RSSNewsConnector(BaseHTTPConnector):
    provider_name = "rss"

    def fetch(self, ticker: str) -> list[dict]:
        if not self.use_network:
            return SampleNewsConnector().fetch(ticker)
        xml_text = self.get_text(f"https://news.google.com/rss/search?q={ticker}%20stock")
        root = ET.fromstring(xml_text)
        items = []
        for item in root.findall('.//item')[:5]:
            items.append({
                'title': item.findtext('title', default=''),
                'link': item.findtext('link', default=''),
                'published_at': item.findtext('pubDate', default=''),
                'content': item.findtext('description', default=''),
            })
        return items
