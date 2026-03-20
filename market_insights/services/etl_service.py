"""ETL service — orchestrates extract → clean → features → load pipeline.

Improvements over v1:
- multi-source document ingestion (fundamentals, news, SEC filings)
- provider metadata tracking
- batch ETL for multiple tickers
- macro data ingestion
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from market_insights.connectors.open_data.fundamentals import MultiFundamentalsConnector, SampleFundamentalsConnector
from market_insights.connectors.open_data.news import MultiNewsConnector, SampleNewsConnector
from market_insights.core.config import settings
from market_insights.etl.extractors.price_provider import PriceProviderRouter
from market_insights.etl.loaders.document_loader import replace_documents
from market_insights.etl.loaders.sqlite_loader import load_price_bars
from market_insights.etl.transformers.cleaning import clean_market_data
from market_insights.etl.transformers.features import compute_features

logger = logging.getLogger(__name__)


def run_etl(db: Session, ticker: str, provider: str | None = None) -> dict:
    """Run full ETL pipeline for a single ticker."""
    started = datetime.now(UTC)
    ticker = ticker.upper()

    # ── 1. Extract prices ──────────────────────────────────────────
    router = PriceProviderRouter(use_network=settings.use_network)
    raw_prices = router.fetch_prices(ticker, provider=provider)
    used_provider = (provider or settings.default_price_provider).lower()

    # ── 2. Transform ───────────────────────────────────────────────
    clean = clean_market_data(raw_prices)
    featured = compute_features(clean)

    # ── 3. Load prices ─────────────────────────────────────────────
    rows = [
        {
            "ticker": row["ticker"],
            "date": row["date"].date() if hasattr(row["date"], "date") else row["date"],
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }
        for _, row in clean.iterrows()
    ]
    loaded_bars = load_price_bars(db, ticker, rows, source=used_provider)

    # ── 4. Ingest documents ────────────────────────────────────────
    docs: list[dict] = []

    # 4a. Fundamentals
    try:
        if settings.use_network:
            fundamentals = MultiFundamentalsConnector().fetch(ticker)
        else:
            fundamentals = SampleFundamentalsConnector().fetch(ticker)
        fund_source = fundamentals.pop("_source", "sample")
        docs.append({
            "document_type": "fundamentals_snapshot",
            "title": f"{ticker} fundamentals ({fund_source})",
            "published_at": started.isoformat(),
            "url": "",
            "content": _format_fundamentals(fundamentals),
        })
    except Exception as exc:
        logger.warning("Fundamentals ingestion failed for %s: %s", ticker, exc)
        fundamentals = {}

    # 4b. News
    try:
        if settings.use_network:
            news_items = MultiNewsConnector().fetch(ticker, max_items=10)
        else:
            news_items = SampleNewsConnector().fetch(ticker)

        for item in news_items:
            docs.append({
                "document_type": "news",
                "title": item.get("title", "news"),
                "published_at": item.get("published_at", ""),
                "url": item.get("link", ""),
                "content": item.get("content", ""),
            })
    except Exception as exc:
        logger.warning("News ingestion failed for %s: %s", ticker, exc)

    # 4c. SEC filings (if network and CIK available)
    if settings.use_network:
        try:
            from market_insights.connectors.open_data.fundamentals import SECCompanyFactsConnector
            sec = SECCompanyFactsConnector(use_network=True)
            sec_data = sec.fetch(ticker)
            docs.append({
                "document_type": "sec_filing",
                "title": f"{ticker} SEC EDGAR company facts",
                "published_at": started.isoformat(),
                "url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{sec_data.get('cik', '')}.json",
                "content": _format_fundamentals(sec_data),
            })
        except Exception as exc:
            logger.debug("SEC ingestion skipped for %s: %s", ticker, exc)

    loaded_docs = replace_documents(db, ticker, source="open_data", docs=docs) if docs else 0

    elapsed = (datetime.now(UTC) - started).total_seconds()

    return {
        "ticker": ticker,
        "provider": used_provider,
        "loaded_rows": loaded_bars,
        "feature_rows": len(featured),
        "loaded_docs": loaded_docs,
        "elapsed_seconds": round(elapsed, 2),
        "timestamp": started.isoformat(),
    }


def run_batch_etl(db: Session, tickers: list[str], provider: str | None = None) -> list[dict]:
    """Run ETL for multiple tickers, collecting results."""
    results = []
    for ticker in tickers:
        try:
            result = run_etl(db, ticker, provider=provider)
            result["status"] = "ok"
        except Exception as exc:
            result = {"ticker": ticker.upper(), "status": "error", "error": str(exc)}
        results.append(result)
    return results


def _format_fundamentals(data: dict) -> str:
    """Format fundamentals dict as readable text for RAG ingestion."""
    lines = []
    for k, v in sorted(data.items()):
        if k.startswith("_"):
            continue
        if isinstance(v, float):
            lines.append(f"{k}: {v:.4f}")
        else:
            lines.append(f"{k}: {v}")
    return "\n".join(lines)
