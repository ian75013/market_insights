"""Pydantic response models for the API."""

from __future__ import annotations

from pydantic import BaseModel


class FairValueResponse(BaseModel):
    ticker: str
    current_price: float
    fair_value: float
    upside_pct: float
    confidence: float
    factors: dict
    method: str = "baseline_multifactor"


class ComparableInsightResponse(BaseModel):
    ticker: str
    timeframe: str
    generated_at: str
    summary: dict
    quotes: dict
    technical: dict
    levels: dict
    signals: dict
    fundamental_rag: dict
    narrative: str
    disclaimer: str


class InsightResponse(BaseModel):
    ticker: str
    generated_at: str
    score: float
    fair_value: float
    analysis: str
    technicals: dict
    fundamentals: dict
    sources: list[dict]
    comparable: ComparableInsightResponse | None = None


class ProviderStatus(BaseModel):
    name: str
    available: bool
    needs_key: bool
    needs_network: bool


class ETLResult(BaseModel):
    ticker: str
    provider: str
    loaded_rows: int
    feature_rows: int
    loaded_docs: int
    elapsed_seconds: float
    timestamp: str
