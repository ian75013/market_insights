from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from market_insights.db.bootstrap import init_db
from market_insights.db.session import get_db
from market_insights.schemas.market import FairValueResponse, InsightResponse
from market_insights.services.etl_service import run_etl
from market_insights.services.market_service import MarketInsightService


init_db()
app = FastAPI(title="Market Insights API", version="1.0.0")
service = MarketInsightService()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tickers")
def tickers():
    return {"tickers": ["AAPL", "MSFT", "NVDA"]}


@app.post("/etl/run")
def run_pipeline(ticker: str, db: Session = Depends(get_db)):
    try:
        return run_etl(db, ticker)
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
