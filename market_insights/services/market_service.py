"""Market Insight Service — core orchestration layer.

Uses multi-source fundamentals, configurable providers, and enriched analysis.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from market_insights.analysis.feature_engineering import compute_market_context
from market_insights.analysis.signal_detection import detect_signals
from market_insights.analysis.target_engine import compute_price_levels
from market_insights.analysis.technical_scoring import build_summary
from market_insights.connectors.open_data.fundamentals import MultiFundamentalsConnector, SampleFundamentalsConnector
from market_insights.core.config import settings
from market_insights.db.models import PriceBar
from market_insights.etl.transformers.features import compute_features
from market_insights.llm.report_generator import generate_report
from market_insights.ml.fair_value import BaselineFairValueModel
from market_insights.rag.store import retrieve_context


class MarketInsightService:
    def __init__(self) -> None:
        self.model = BaselineFairValueModel()

    def _get_fundamentals(self, ticker: str) -> dict:
        """Fetch fundamentals with multi-source fallback."""
        if settings.use_network:
            try:
                result = MultiFundamentalsConnector().fetch(ticker)
                result.pop("_source", None)
                return result
            except Exception:
                pass
        return SampleFundamentalsConnector().fetch(ticker)

    def _load_df(self, db: Session, ticker: str) -> pd.DataFrame:
        rows = db.execute(
            select(PriceBar).where(PriceBar.ticker == ticker.upper()).order_by(PriceBar.date.asc())
        ).scalars().all()
        if not rows:
            raise ValueError(f"No price data found for ticker={ticker}. Run ETL first.")
        return pd.DataFrame(
            [
                {
                    "ticker": r.ticker,
                    "date": pd.to_datetime(r.date),
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                }
                for r in rows
            ]
        )

    def compute_fair_value(self, db: Session, ticker: str) -> dict:
        fundamentals = self._get_fundamentals(ticker)
        df = compute_features(self._load_df(db, ticker))
        latest = df.iloc[-1]
        result = self.model.predict(df, fundamentals=fundamentals)
        current_price = float(latest["close"])
        upside_pct = round((result.fair_value / current_price - 1.0) * 100, 2)
        return {
            "ticker": ticker.upper(),
            "current_price": round(current_price, 2),
            "fair_value": result.fair_value,
            "upside_pct": upside_pct,
            "confidence": result.confidence,
            "factors": result.factors,
            "method": "baseline_multifactor",
        }

    def get_rag_sources(self, db: Session, ticker: str) -> list[dict]:
        return retrieve_context(db, ticker.upper(), query="earnings growth debt valuation risk catalysts", top_k=5)

    def generate_insight(self, db: Session, ticker: str) -> dict:
        ticker = ticker.upper()
        df = compute_features(self._load_df(db, ticker))
        fair = self.compute_fair_value(db, ticker)
        technicals = df.iloc[-1][
            ["rsi_14", "volatility_20", "trend_signal", "momentum_20", "drawdown", "sma_20", "sma_50", "sma_200"]
        ].to_dict()
        fundamentals = self._get_fundamentals(ticker)
        rag_context = self.get_rag_sources(db, ticker)

        score = round(
            min(
                1.0,
                max(
                    0.0,
                    0.30
                    + 0.18 * (1 if technicals["trend_signal"] else 0)
                    + 0.20 * max(-0.2, min(0.2, technicals["momentum_20"]))
                    + 0.12 * fair["confidence"]
                    + 0.12 * max(-0.1, min(0.3, fundamentals.get("revenue_growth", 0.0)))
                    - 0.08 * max(0.0, fundamentals.get("debt_to_equity", 1.0) - 1.5),
                ),
            ),
            2,
        )

        market_context = compute_market_context(df)
        signals = detect_signals(df)
        levels = compute_price_levels(df)
        summary = build_summary(
            technicals=technicals,
            fair_value=fair["fair_value"],
            current_price=fair["current_price"],
            levels=levels,
            signals=signals,
            score=score,
        )

        analysis = generate_report(
            ticker=ticker,
            current_price=fair["current_price"],
            fair_value=fair["fair_value"],
            score=score,
            technicals=technicals,
            rag_context=rag_context,
            fundamentals=fundamentals,
            summary=summary,
            levels=levels,
            signals=signals,
            market_context=market_context,
        )
        generated_at = datetime.now(UTC).isoformat()
        technical_payload = {k: round(float(v), 4) for k, v in technicals.items()}
        comparable = {
            "ticker": ticker,
            "timeframe": "1D",
            "generated_at": generated_at,
            "summary": summary,
            "quotes": market_context,
            "technical": technical_payload,
            "levels": levels,
            "signals": signals,
            "fundamental_rag": {
                "summary": (
                    f"Croissance CA {fundamentals.get('revenue_growth', 'n/a')}, "
                    f"EPS {fundamentals.get('eps_growth', 'n/a')}, dette {fundamentals.get('debt_to_equity', 'n/a')}"
                ),
                "sources": rag_context,
            },
            "narrative": analysis,
            "disclaimer": "Contenu informatif et analytique, non personnalisé, ne constituant pas un conseil en investissement.",
        }

        # ── Scores dict for hybrid service ─────────────────────────
        scores = {
            "overall_score": score,
            "trend_score": 0.55 + 0.25 * float(technicals["trend_signal"]) + 0.15 * technicals["momentum_20"],
            "confidence_score": fair["confidence"],
        }

        return {
            "ticker": ticker,
            "generated_at": generated_at,
            "score": score,
            "scores": scores,
            "last_price": fair["current_price"],
            "fair_value": fair["fair_value"],
            "analysis": analysis,
            "technicals": technical_payload,
            "fundamentals": fundamentals,
            "sources": rag_context,
            "comparable": comparable,
            "summary": summary,
        }
