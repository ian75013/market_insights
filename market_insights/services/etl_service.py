from __future__ import annotations

from sqlalchemy.orm import Session

from market_insights.connectors.open_data.fundamentals import SampleFundamentalsConnector
from market_insights.connectors.open_data.news import SampleNewsConnector, RSSNewsConnector
from market_insights.core.config import settings
from market_insights.etl.extractors.price_provider import PriceProviderRouter
from market_insights.etl.loaders.document_loader import replace_documents
from market_insights.etl.loaders.sqlite_loader import load_price_bars
from market_insights.etl.transformers.cleaning import clean_market_data
from market_insights.etl.transformers.features import compute_features


def run_etl(db: Session, ticker: str, provider: str | None = None) -> dict:
    router = PriceProviderRouter(use_network=settings.use_network)
    raw_prices = router.fetch_prices(ticker, provider=provider)
    clean = clean_market_data(raw_prices)
    featured = compute_features(clean)
    used_provider = (provider or settings.default_price_provider).lower()

    rows = [
        {
            "ticker": row["ticker"],
            "date": row["date"].date(),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }
        for _, row in clean.iterrows()
    ]
    loaded_bars = load_price_bars(db, ticker.upper(), rows, source=used_provider)

    fundamentals = SampleFundamentalsConnector().fetch(ticker)
    docs = [
        {
            "document_type": "fundamentals_snapshot",
            "title": f"{ticker.upper()} fundamentals snapshot",
            "published_at": "",
            "url": "",
            "content": str(fundamentals),
        }
    ]
    news_items = RSSNewsConnector(use_network=settings.use_network).fetch(ticker)
    if not news_items:
        news_items = SampleNewsConnector().fetch(ticker)
    docs.extend([
        {
            "document_type": "news",
            "title": item.get("title", "news"),
            "published_at": item.get("published_at", ""),
            "url": item.get("link", ""),
            "content": item.get("content", ""),
        }
        for item in news_items
    ])
    loaded_docs = replace_documents(db, ticker.upper(), source="open_data", docs=docs)

    return {
        "ticker": ticker.upper(),
        "provider": used_provider,
        "loaded_rows": loaded_bars,
        "feature_rows": len(featured),
        "loaded_docs": loaded_docs,
    }
