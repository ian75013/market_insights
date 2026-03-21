"""Market Insights API v3 — FastAPI application.

New in v3:
- /providers          : list available data providers + status
- /etl/batch          : batch ETL for multiple tickers
- /macro              : macro dashboard (FRED or sample)
- /fundamentals/{t}   : multi-source fundamentals
- /news/{ticker}      : multi-source news feed
- /cache/stats        : cache monitoring
- /cache/clear        : cache invalidation
"""

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from market_insights.core.cache import cache_store
from market_insights.core.config import settings
from market_insights.db.bootstrap import init_db
from market_insights.db.session import get_db
from market_insights.etl.extractors.price_provider import PriceProviderRouter
from market_insights.schemas.market import ComparableInsightResponse, FairValueResponse, InsightResponse
from market_insights.services.etl_service import run_batch_etl, run_etl
from market_insights.services.hybrid_insight_service import HybridInsightService
from market_insights.services.market_service import MarketInsightService

init_db()

app = FastAPI(
    title="Market Insights API",
    version="3.0.0",
    description=(
        "Plateforme de recherche actions — ETL multi-source, analyse technique, "
        "juste valeur, RAG documentaire, insight hybride."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = MarketInsightService()
hybrid_service = HybridInsightService()


# ━━ Health & Info ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "version": "3.0.0",
        "network_enabled": settings.use_network,
        "default_provider": settings.default_price_provider,
    }


@app.get("/sources", tags=["system"])
def sources():
    return {
        "price_providers": ["sample", "stooq", "yahoo", "alpha_vantage", "coingecko", "ibkr", "auto"],
        "fundamentals_providers": ["sample", "yahoo", "alpha_vantage", "fmp", "sec_edgar", "multi"],
        "news_providers": ["sample", "rss", "alpha_vantage", "multi"],
        "macro_providers": ["sample", "fred"],
    }


@app.get("/providers", tags=["system"])
def providers():
    """Live provider availability status."""
    router = PriceProviderRouter()
    return {
        "price_providers": router.available_providers(),
        "network_enabled": settings.use_network,
        "api_keys_configured": {
            "alpha_vantage": bool(settings.alpha_vantage_api_key),
            "fred": bool(settings.fred_api_key),
            "fmp": bool(settings.fmp_api_key),
        },
    }


# ━━ ETL ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/etl/run", tags=["etl"])
def run_pipeline(
    ticker: str = Query(..., min_length=1),
    provider: str = Query("sample"),
    db: Session = Depends(get_db),
):
    try:
        return run_etl(db, ticker=ticker, provider=provider)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/etl/batch", tags=["etl"])
def run_batch_pipeline(
    tickers: str = Query(..., description="Comma-separated tickers: AAPL,MSFT,NVDA"),
    provider: str = Query("sample"),
    db: Session = Depends(get_db),
):
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        raise HTTPException(status_code=400, detail="No tickers provided")
    if len(ticker_list) > 20:
        raise HTTPException(status_code=400, detail="Max 20 tickers per batch")
    return run_batch_etl(db, ticker_list, provider=provider)


# ━━ Analysis ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/fair-value/{ticker}", response_model=FairValueResponse, tags=["analysis"])
def fair_value(ticker: str, db: Session = Depends(get_db)):
    try:
        return service.compute_fair_value(db, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/insights/{ticker}", tags=["analysis"])
def insight(ticker: str, db: Session = Depends(get_db)):
    try:
        return service.generate_insight(db, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/insights/{ticker}/comparable", tags=["analysis"])
def comparable_insight(ticker: str, db: Session = Depends(get_db)):
    try:
        full = service.generate_insight(db, ticker)
        return full.get("comparable", {})
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/insights/{ticker}/hybrid", tags=["analysis"])
def hybrid_insight(ticker: str, db: Session = Depends(get_db)):
    try:
        return hybrid_service.generate_hybrid_insight(db, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ━━ Data ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/rag/sources/{ticker}", tags=["data"])
def rag_sources(ticker: str, db: Session = Depends(get_db)):
    return {"ticker": ticker.upper(), "sources": service.get_rag_sources(db, ticker)}


@app.get("/fundamentals/{ticker}", tags=["data"])
def fundamentals(ticker: str):
    """Fetch fundamentals from best available source."""
    try:
        from market_insights.connectors.open_data.fundamentals import MultiFundamentalsConnector, SampleFundamentalsConnector
        if settings.use_network:
            result = MultiFundamentalsConnector().fetch(ticker)
        else:
            result = SampleFundamentalsConnector().fetch(ticker)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/news/{ticker}", tags=["data"])
def news(ticker: str, limit: int = Query(10, ge=1, le=50)):
    """Fetch news from best available source."""
    try:
        from market_insights.connectors.open_data.news import MultiNewsConnector, SampleNewsConnector
        if settings.use_network:
            items = MultiNewsConnector().fetch(ticker, max_items=limit)
        else:
            items = SampleNewsConnector().fetch(ticker)
        return {"ticker": ticker.upper(), "count": len(items), "items": items}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/macro", tags=["data"])
def macro_dashboard():
    """Macro indicators from FRED or sample data."""
    try:
        from market_insights.connectors.open_data.macro import FREDConnector, SampleMacroConnector
        fred = FREDConnector()
        if fred.available():
            return {"source": "fred", "data": fred.fetch_macro_dashboard()}
        return {"source": "sample", "data": SampleMacroConnector().fetch()}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ━━ Cache management ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/cache/stats", tags=["system"])
def cache_stats():
    return cache_store.stats()


@app.post("/cache/clear", tags=["system"])
def cache_clear(prefix: str = Query("", description="Clear keys matching this prefix (empty = all)")):
    cleared = cache_store.invalidate(prefix)
    return {"cleared_keys": cleared, "prefix": prefix or "(all)"}
