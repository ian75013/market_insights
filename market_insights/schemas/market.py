from datetime import date
from pydantic import BaseModel


class PriceBarSchema(BaseModel):
    ticker: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class FairValueResponse(BaseModel):
    ticker: str
    current_price: float
    fair_value: float
    upside_pct: float
    confidence: float
    factors: dict


class InsightResponse(BaseModel):
    ticker: str
    generated_at: str
    score: float
    fair_value: float
    analysis: str
    technicals: dict
    rag_context: list[str]
