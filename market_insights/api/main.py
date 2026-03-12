from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from market_insights.db.bootstrap import init_db
from market_insights.db.session import get_db
from market_insights.schemas.market import ComparableInsightResponse, FairValueResponse, InsightResponse
from market_insights.services.etl_service import run_etl
from market_insights.services.market_service import MarketInsightService
from market_insights.services.hybrid_insight_service import HybridInsightService


init_db()
app = FastAPI(title="Market Insights API", version="2.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
service = MarketInsightService()
hybrid_service = HybridInsightService()


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.1.0"}


@app.get("/sources")
def sources():
    return {
        "price_providers": ["sample", "stooq", "ibkr"],
        "document_providers": ["sample_fundamentals", "sample_news", "rss", "sec_company_facts"],
    }


@app.post("/etl/run")
def run_pipeline(
    ticker: str = Query(..., min_length=1),
    provider: str = Query("sample"),
    db: Session = Depends(get_db),
):
    try:
        return run_etl(db, ticker=ticker, provider=provider)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/fair-value/{ticker}", response_model=FairValueResponse)
def fair_value(ticker: str, db: Session = Depends(get_db)):
    try:
        return service.compute_fair_value(db, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/insights/{ticker}", response_model=InsightResponse)
def insight(ticker: str, db: Session = Depends(get_db)):
    try:
        return service.generate_insight(db, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/insights/{ticker}/comparable", response_model=ComparableInsightResponse)
def comparable_insight(ticker: str, db: Session = Depends(get_db)):
    try:
        return service.generate_insight(db, ticker)["comparable"]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/rag/sources/{ticker}")
def rag_sources(ticker: str, db: Session = Depends(get_db)):
    return {"ticker": ticker.upper(), "sources": service.get_rag_sources(db, ticker)}


@app.get("/insights/{ticker}/hybrid")
def hybrid_insight(ticker: str, db: Session = Depends(get_db)):
    try:
        return hybrid_service.generate_hybrid_insight(db, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
