from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from market_insights.services.market_service import MarketInsightService


class HybridInsightService:
    def __init__(self) -> None:
        self.market_service = MarketInsightService()

    def generate_hybrid_insight(self, db: Session, ticker: str) -> dict[str, Any]:
        # Each sub-call is wrapped individually so one failure
        # doesn't bring down the whole hybrid response.
        try:
            insight = self.market_service.generate_insight(db, ticker)
        except Exception as exc:
            raise ValueError(
                f"Hybrid: generate_insight failed for {ticker}: {exc}"
            ) from exc

        try:
            fair_value = self.market_service.compute_fair_value(db, ticker)
        except Exception:
            # Fallback: extract fair_value from the insight that succeeded
            fair_value = {
                "fair_value": insight.get("fair_value", 0),
                "current_price": insight.get("last_price", 0),
                "upside_pct": 0,
                "confidence": insight.get("scores", {}).get("confidence_score", 0),
            }

        try:
            rag_sources = self.market_service.get_rag_sources(db, ticker)
        except Exception:
            rag_sources = []

        comparable = insight.get("comparable", {})
        current_price = float(insight.get("last_price") or 0.0)
        model_price = float(fair_value.get("fair_value") or current_price or 0.0)

        gap_pct = 0.0
        if current_price:
            gap_pct = ((model_price - current_price) / current_price) * 100.0

        catalysts = []
        risks = []
        for src in rag_sources[:6]:
            title = src.get("title") or src.get("source") or "source"
            snippet = src.get("snippet") or ""
            low = f"{title} {snippet}".lower()
            if any(
                k in low
                for k in ["growth", "beat", "upgrade", "partnership", "ai", "revenue"]
            ):
                catalysts.append(title)
            if any(
                k in low
                for k in ["risk", "downgrade", "debt", "lawsuit", "weak", "decline"]
            ):
                risks.append(title)

        if not catalysts:
            catalysts = ["Momentum technique favorable"]
        if not risks:
            risks = ["Volatilité de marché à surveiller"]

        verdict = "neutral"
        if gap_pct > 7 and insight.get("scores", {}).get("trend_score", 0) >= 0.55:
            verdict = "bullish"
        elif gap_pct < -7 and insight.get("scores", {}).get("trend_score", 0) <= 0.45:
            verdict = "bearish"

        executive_summary = self._build_executive_summary(
            ticker=ticker.upper(),
            current_price=current_price,
            model_price=model_price,
            gap_pct=gap_pct,
            insight=insight,
            verdict=verdict,
        )

        return {
            "ticker": ticker.upper(),
            "verdict": verdict,
            "executive_summary": executive_summary,
            "technical": insight,
            "fair_value": fair_value,
            "comparable": comparable,
            "rag": {
                "sources": rag_sources,
                "top_catalysts": catalysts[:3],
                "top_risks": risks[:3],
            },
            "hybrid": {
                "current_price": current_price,
                "model_price": model_price,
                "upside_pct": round(gap_pct, 2),
                "confidence": insight.get("scores", {}).get("confidence_score", 0),
                "opinion": insight.get("summary", {}).get("opinion", "n/a"),
            },
            "disclaimer": (
                "Analyse générée automatiquement à titre informatif. "
                "Ce contenu ne constitue pas un conseil en investissement."
            ),
        }

    def _build_executive_summary(
        self,
        ticker: str,
        current_price: float,
        model_price: float,
        gap_pct: float,
        insight: dict[str, Any],
        verdict: str,
    ) -> str:
        summary = insight.get("summary", {})
        scores = insight.get("scores", {})
        trend = summary.get("short_trend", "neutre")
        long_trend = summary.get("long_trend", "neutre")
        opinion = summary.get("opinion", "n/a")
        confidence = round(float(scores.get("confidence_score", 0)) * 100)

        if verdict == "bullish":
            angle = "Le scénario hybride reste constructif"
        elif verdict == "bearish":
            angle = "Le scénario hybride reste fragile"
        else:
            angle = "Le scénario hybride reste équilibré"

        return (
            f"{angle} sur {ticker}. Le prix actuel ressort à "
            f"{current_price:.2f} tandis que le modèle de juste valeur "
            f"estime un niveau autour de {model_price:.2f}, soit un écart de "
            f"{gap_pct:.2f}%. La tendance de court terme est {trend} et "
            f"la tendance de fond {long_trend}. L'opinion technique courante "
            f"est '{opinion}' avec un niveau de confiance proche de "
            f"{confidence}%."
        )
