"""Market Insights API v4 — FastAPI application.

New in v4:
- /llm/providers           : list LLM providers + models + availability
- /llm/chat                : RAG-powered chat with LLM selector
- /chart/candlestick/{t}   : annotated OHLCV with per-bar signals
- /rag/index/{t}           : manually trigger RAG index
- /rag/stats               : vector store stats
"""

import logging

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from market_insights.core.cache import cache_store
from market_insights.core.config import settings
from market_insights.db.bootstrap import init_db
from market_insights.db.session import get_db
from market_insights.etl.extractors.price_provider import PriceProviderRouter, canonical_ticker
from market_insights.schemas.market import FairValueResponse
from market_insights.services.etl_service import run_batch_etl, run_etl
from market_insights.services.hybrid_insight_service import HybridInsightService
from market_insights.services.market_service import MarketInsightService
from market_insights.llm.providers import is_public_provider, list_providers, public_provider_names

logger = logging.getLogger("mi.scheduler")

@asynccontextmanager
async def lifespan(app_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Market Insights API",
    version="4.0.0",
    description=(
        "Plateforme de recherche actions — ETL multi-source, "
        "analyse technique, RAG vectoriel, LLM multi-provider, "
        "chandeliers annotés."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = MarketInsightService()
hybrid_service = HybridInsightService()


def _validate_llm_backend(backend: str | None) -> str | None:
    if backend and not is_public_provider(backend):
        raise HTTPException(
            status_code=400,
            detail="Le provider 'ollama' n'est pas exposé par l'application. Utilise 'litellm'.",
        )
    return backend


def _active_public_backend() -> str:
    backend = (settings.llm_backend or "litellm").lower()
    return backend if is_public_provider(backend) else "litellm"


# ━━ Health & Info ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "version": "4.0.0",
        "network_enabled": settings.use_network,
        "default_provider": settings.default_price_provider,
    }


@app.get("/sources", tags=["system"])
def sources():
    return {
        "price_providers": [
            "sample",
            "stooq",
            "yahoo",
            "alpha_vantage",
            "coingecko",
            "ibkr",
            "auto",
        ],
        "fundamentals_providers": [
            "sample",
            "yahoo",
            "alpha_vantage",
            "fmp",
            "sec_edgar",
            "multi",
        ],
        "news_providers": ["sample", "rss", "alpha_vantage", "multi"],
        "macro_providers": ["sample", "fred"],
        "llm_providers": [
            *public_provider_names(),
        ],
    }


@app.get("/providers", tags=["system"])
def providers():
    router = PriceProviderRouter()
    return {
        "price_providers": router.available_providers(),
        "network_enabled": settings.use_network,
        "api_keys_configured": {
            "alpha_vantage": bool(settings.alpha_vantage_api_key),
            "fred": bool(settings.fred_api_key),
            "fmp": bool(settings.fmp_api_key),
            "litellm": bool(settings.litellm_api_key),
            "openai": bool(settings.openai_api_key),
            "anthropic": bool(settings.anthropic_api_key),
            "mistral": bool(settings.mistral_api_key),
            "groq": bool(settings.groq_api_key),
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
    tickers: str = Query(...),
    provider: str = Query("sample"),
    db: Session = Depends(get_db),
):
    ticker_list = [canonical_ticker(t.strip()) for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        raise HTTPException(status_code=400, detail="No tickers provided")
    return run_batch_etl(db, ticker_list, provider=provider)


# ━━ Analysis ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.get("/fair-value/{ticker}", response_model=FairValueResponse, tags=["analysis"])
def fair_value(ticker: str, db: Session = Depends(get_db)):
    ticker = canonical_ticker(ticker)
    try:
        return service.compute_fair_value(db, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/insights/{ticker}", tags=["analysis"])
def insight(ticker: str, db: Session = Depends(get_db)):
    ticker = canonical_ticker(ticker)
    try:
        return service.generate_insight(db, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/insights/{ticker}/comparable", tags=["analysis"])
def comparable_insight(ticker: str, db: Session = Depends(get_db)):
    ticker = canonical_ticker(ticker)
    try:
        full = service.generate_insight(db, ticker)
        return full.get("comparable", {})
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/insights/{ticker}/hybrid", tags=["analysis"])
def hybrid_insight(ticker: str, db: Session = Depends(get_db)):
    ticker = canonical_ticker(ticker)
    try:
        return hybrid_service.generate_hybrid_insight(db, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ━━ Candlestick chart ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.get("/chart/candlestick/{ticker}", tags=["chart"])
def candlestick_chart(ticker: str, db: Session = Depends(get_db)):
    """Return OHLCV bars with per-bar signal annotations for chart rendering."""
    ticker = canonical_ticker(ticker)
    try:
        from market_insights.analysis.candlestick_engine import annotate_candlesticks

        df = service._load_df(db, ticker)
        bars = annotate_candlesticks(df)
        # Summary of all detected signals
        all_signals = []
        for bar in bars:
            for s in bar.get("signals", []):
                s["date"] = bar["date"]
                all_signals.append(s)
        return {
            "ticker": ticker.upper(),
            "bars": bars,
            "signal_summary": {
                "total": len(all_signals),
                "bullish": len(
                    [s for s in all_signals if s.get("severity") == "bullish"]
                ),
                "bearish": len(
                    [s for s in all_signals if s.get("severity") == "bearish"]
                ),
                "neutral": len(
                    [s for s in all_signals if s.get("severity") == "neutral"]
                ),
            },
            "signals": all_signals[-20:],  # last 20 signals for display
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ━━ Data ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.get("/rag/sources/{ticker}", tags=["rag"])
def rag_sources(ticker: str, db: Session = Depends(get_db)):
    ticker = canonical_ticker(ticker)
    return {"ticker": ticker, "sources": service.get_rag_sources(db, ticker)}


@app.post("/rag/index/{ticker}", tags=["rag"])
def rag_index(ticker: str, db: Session = Depends(get_db)):
    """Manually trigger RAG vector indexing for a ticker."""
    ticker = canonical_ticker(ticker)
    from market_insights.rag.store import index_documents

    count = index_documents(db, ticker)
    return {"ticker": ticker, "indexed_chunks": count}


@app.get("/rag/stats", tags=["rag"])
def rag_stats():
    from market_insights.rag.embeddings import vector_store

    return vector_store.stats()


@app.get("/fundamentals/{ticker}", tags=["data"])
def fundamentals(ticker: str):
    ticker = canonical_ticker(ticker)
    try:
        from market_insights.connectors.open_data.fundamentals import (
            MultiFundamentalsConnector,
            SampleFundamentalsConnector,
        )

        if settings.use_network:
            result = MultiFundamentalsConnector().fetch(ticker)
        else:
            result = SampleFundamentalsConnector().fetch(ticker)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/news/{ticker}", tags=["data"])
def news(ticker: str, limit: int = Query(10, ge=1, le=50)):
    ticker = canonical_ticker(ticker)
    try:
        from market_insights.connectors.open_data.news import (
            MultiNewsConnector,
            SampleNewsConnector,
        )

        if settings.use_network:
            items = MultiNewsConnector().fetch(ticker, max_items=limit)
        else:
            items = SampleNewsConnector().fetch(ticker)
        return {"ticker": ticker.upper(), "count": len(items), "items": items}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/macro", tags=["data"])
def macro_dashboard(db: Session = Depends(get_db)):
    try:
        from market_insights.db.models import MacroMetric
        from market_insights.connectors.open_data.macro import (
            FREDConnector,
            SampleMacroConnector,
        )

        rows = db.execute(select(MacroMetric).order_by(MacroMetric.metric_key.asc())).scalars().all()
        if rows:
            data = {row.metric_key: row.metric_value for row in rows}
            as_of = max(row.updated_at for row in rows if row.updated_at is not None)
            source = rows[0].source if rows[0].source else "db"
            return {"source": source, "as_of": as_of.isoformat() if as_of else None, "data": data}

        fred = FREDConnector()
        if fred.available():
            return {"source": "fred", "data": fred.fetch_macro_dashboard()}
        return {"source": "sample", "data": SampleMacroConnector().fetch()}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ━━ LLM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.get("/llm/providers", tags=["llm"])
def llm_providers():
    """List all LLM providers with availability and model lists."""
    return {"providers": list_providers(), "active_backend": _active_public_backend()}


class ChatRequest(BaseModel):
    question: str
    ticker: str = "AAPL"
    llm_backend: str | None = None
    llm_model: str | None = None
    language: str = "fr"
    top_k: int = 5


@app.post("/llm/chat", tags=["llm"])
def llm_chat(req: ChatRequest, db: Session = Depends(get_db)):
    """RAG-powered chat: retrieve context, build the prompt, then generate."""
    try:
        from market_insights.rag.chat import rag_chat

        llm_backend = _validate_llm_backend(req.llm_backend)
        return rag_chat(
            db,
            ticker=req.ticker,
            question=req.question,
            llm_backend=llm_backend,
            llm_model=req.llm_model,
            language=req.language,
            top_k=req.top_k,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc




@app.post("/llm/chat/stream", tags=["llm"])
def llm_chat_stream(req: ChatRequest, db: Session = Depends(get_db)):
    """RAG chat with Server-Sent Events streaming."""
    from market_insights.rag.chat import rag_chat_stream

    llm_backend = _validate_llm_backend(req.llm_backend)

    def gen():
        yield from rag_chat_stream(
            db, ticker=req.ticker, question=req.question,
            llm_backend=llm_backend, llm_model=req.llm_model,
            language=req.language, top_k=req.top_k,
        )

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })

# ━━ Cache management ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.get("/cache/stats", tags=["system"])
def cache_stats():
    return cache_store.stats()


@app.post("/cache/clear", tags=["system"])
def cache_clear(prefix: str = Query("")):
    cleared = cache_store.invalidate(prefix)
    return {"cleared_keys": cleared, "prefix": prefix or "(all)"}
