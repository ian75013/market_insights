from datetime import datetime, UTC


def generate_report(ticker: str, current_price: float, fair_value: float, score: float, technicals: dict, rag_context: list[str]) -> str:
    trend = "haussière" if technicals.get("trend_signal", 0) == 1 else "prudente"
    upside = ((fair_value / current_price) - 1.0) * 100 if current_price else 0.0
    context_block = " | ".join(rag_context) if rag_context else "Aucun contexte documentaire disponible."
    return (
        f"[{datetime.now(UTC).isoformat()}] Analyse {ticker}: la dynamique technique est {trend}. "
        f"Le prix courant est {current_price:.2f} et la juste valeur estimée est {fair_value:.2f}, "
        f"soit un potentiel de {upside:.2f}%. "
        f"Le score global est de {score:.2f}/1. "
        f"RSI={technicals.get('rsi_14', 50):.2f}, volatilité 20j={technicals.get('volatility_20', 0):.4f}. "
        f"Contexte RAG: {context_block}"
    )
