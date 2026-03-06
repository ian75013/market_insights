from datetime import datetime, UTC
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from market_insights.db.models import PriceBar
from market_insights.llm.report_generator import generate_report
from market_insights.ml.fair_value import BaselineFairValueModel
from market_insights.rag.store import retrieve_context
from market_insights.etl.transformers.features import compute_features


class MarketInsightService:
    def __init__(self) -> None:
        self.model = BaselineFairValueModel()

    def _load_df(self, db: Session, ticker: str) -> pd.DataFrame:
        rows = db.execute(select(PriceBar).where(PriceBar.ticker == ticker).order_by(PriceBar.date.asc())).scalars().all()
        if not rows:
            raise ValueError(f"No price data found for ticker={ticker}")
        return pd.DataFrame([
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
        ])

    def compute_fair_value(self, db: Session, ticker: str) -> dict:
        df = compute_features(self._load_df(db, ticker))
        latest = df.iloc[-1]
        result = self.model.predict(df)
        current_price = float(latest["close"])
        upside_pct = round((result.fair_value / current_price - 1.0) * 100, 2)
        return {
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "fair_value": result.fair_value,
            "upside_pct": upside_pct,
            "confidence": result.confidence,
            "factors": result.factors,
        }

    def generate_insight(self, db: Session, ticker: str) -> dict:
        df = compute_features(self._load_df(db, ticker))
        fair = self.compute_fair_value(db, ticker)
        technicals = df.iloc[-1][["rsi_14", "volatility_20", "trend_signal", "momentum_20", "drawdown"]].to_dict()
        rag_context = retrieve_context(ticker)

        score = round(
            min(
                1.0,
                max(
                    0.0,
                    0.35
                    + 0.25 * (1 if technicals["trend_signal"] else 0)
                    + 0.25 * max(-0.2, min(0.2, technicals["momentum_20"]))
                    + 0.15 * fair["confidence"],
                ),
            ),
            2,
        )
        analysis = generate_report(
            ticker=ticker,
            current_price=fair["current_price"],
            fair_value=fair["fair_value"],
            score=score,
            technicals=technicals,
            rag_context=rag_context,
        )
        return {
            "ticker": ticker,
            "generated_at": datetime.now(UTC).isoformat(),
            "score": score,
            "fair_value": fair["fair_value"],
            "analysis": analysis,
            "technicals": {k: round(float(v), 4) for k, v in technicals.items()},
            "rag_context": rag_context,
        }
