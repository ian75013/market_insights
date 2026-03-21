"""Report generation — uses LLM when available, deterministic fallback otherwise."""

from __future__ import annotations

import logging

from market_insights.llm.providers import get_llm

logger = logging.getLogger(__name__)


def generate_report(
    *,
    ticker: str,
    current_price: float,
    fair_value: float,
    score: float,
    technicals: dict,
    rag_context: list[dict],
    fundamentals: dict,
    summary: dict | None = None,
    levels: dict | None = None,
    signals: dict | None = None,
    market_context: dict | None = None,
    use_llm: bool = False,
    llm_backend: str | None = None,
) -> str:
    summary = summary or {}
    levels = levels or {}
    signals = signals or {"patterns": [], "candles": [], "flags": {}}
    market_context = market_context or {}

    # Build deterministic report (always)
    sources = "; ".join(f"{c['document_type']}:{c['title']}" for c in rag_context[:3]) or "aucune source"
    patterns = ", ".join(signals.get("patterns", [])[:3]) or "aucun pattern majeur"
    candles = ", ".join(signals.get("candles", [])[:2]) or "aucun chandelier décisif"

    deterministic = (
        f"Résumé d'analyse — {ticker}. "
        f"Tendance court terme {summary.get('trend_short', 'neutre')}, tendance de fond {summary.get('trend_long', 'neutre')}. "
        f"Opinion: {summary.get('opinion', 'neutre')}. "
        f"Cours {current_price:.2f}, juste valeur baseline {fair_value:.2f}, score global {score:.2f}. "
        f"Objectif 1 {levels.get('target_1', current_price):.2f} puis objectif 2 {levels.get('target_2', current_price):.2f}. "
        f"Support pivot {levels.get('support', current_price):.2f}, résistance immédiate {levels.get('resistance', current_price):.2f}. "
        f"Le momentum sur 20 périodes ressort à {technicals.get('momentum_20', 0.0):.4f}, le RSI 14 à {technicals.get('rsi_14', 50.0):.2f} et la volatilité 20 à {technicals.get('volatility_20', 0.0):.4f}. "
        f"Les signaux saillants sont: {patterns}; chandeliers détectés: {candles}. "
        f"Sur le plan fondamental, la croissance du chiffre d'affaires est de {fundamentals.get('revenue_growth', 'n/a')}, "
        f"la croissance EPS de {fundamentals.get('eps_growth', 'n/a')} et le debt-to-equity de {fundamentals.get('debt_to_equity', 'n/a')}. "
        f"Le mouvement du jour est de {market_context.get('day_change_pct', 0.0):.2f}% avec un ratio de volume de {market_context.get('volume_ratio', 1.0):.2f}. "
        f"Contexte documentaire utilisé: {sources}. "
        f"Avertissement: contenu analytique non personnalisé, ne constituant pas un conseil en investissement."
    )

    if not use_llm:
        return deterministic

    # Try LLM enhancement
    try:
        llm = get_llm(llm_backend)
        if not llm.available():
            return deterministic

        prompt = f"""Voici les données d'analyse pour {ticker}:

{deterministic}

Réécris ce résumé de manière plus fluide et professionnelle, en conservant TOUS les chiffres et niveaux.
Structure en 3 paragraphes: 1) Situation technique 2) Valorisation 3) Synthèse et niveaux clés.
Reste factuel, pas de conseil en investissement."""

        resp = llm.generate(prompt, system="Tu es un analyste financier senior rédigeant une note de recherche.")
        return resp.text
    except Exception as exc:
        logger.warning("LLM report generation failed, using deterministic: %s", exc)
        return deterministic
