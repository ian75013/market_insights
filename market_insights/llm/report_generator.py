from __future__ import annotations


def generate_report(*, ticker: str, current_price: float, fair_value: float, score: float, technicals: dict, rag_context: list[dict], fundamentals: dict) -> str:
    direction = "haussier" if fair_value >= current_price else "prudent"
    sources = "; ".join(f"{c['document_type']}:{c['title']}" for c in rag_context[:3]) or "aucune source"
    return (
        f"Fiche {ticker} — Vue synthétique. "
        f"Le titre présente un biais {direction} avec un score global de {score:.2f}. "
        f"Prix actuel: {current_price:.2f}. Juste valeur baseline: {fair_value:.2f}. "
        f"RSI14={technicals['rsi_14']:.2f}, volatilité20={technicals['volatility_20']:.4f}, "
        f"momentum20={technicals['momentum_20']:.4f}, trend_signal={int(technicals['trend_signal'])}. "
        f"Fondamentaux maison: revenue_growth={fundamentals.get('revenue_growth', 'n/a')}, "
        f"eps_growth={fundamentals.get('eps_growth', 'n/a')}, debt_to_equity={fundamentals.get('debt_to_equity', 'n/a')}. "
        f"Contexte RAG utilisé: {sources}."
    )
