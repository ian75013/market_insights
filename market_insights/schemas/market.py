from __future__ import annotations

from pydantic import BaseModel


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
    fundamentals: dict
    sources: list[dict]
