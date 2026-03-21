from __future__ import annotations


def _trend_label(short_up: bool, long_up: bool) -> tuple[str, str]:
    if short_up and long_up:
        return "fortement haussière", "haussière"
    if short_up and not long_up:
        return "haussière", "neutre"
    if (not short_up) and long_up:
        return "hésitante", "haussière"
    return "baissière", "baissière"


def build_summary(
    *,
    technicals: dict,
    fair_value: float,
    current_price: float,
    levels: dict,
    signals: dict,
    score: float,
) -> dict:
    short_up = bool(technicals.get("trend_signal", 0))
    long_up = technicals.get("sma_50", 0.0) >= technicals.get(
        "sma_200", technicals.get("sma_50", 0.0)
    )
    trend_short, trend_long = _trend_label(short_up, long_up)

    premium_pct = ((fair_value / current_price) - 1.0) * 100 if current_price else 0.0
    if premium_pct >= 5 and short_up:
        opinion = f"haussier au-dessus de {levels['invalidation']:.2f}"
    elif premium_pct <= -5 and not short_up:
        opinion = f"baissier sous {levels['resistance']:.2f}"
    else:
        opinion = f"neutre entre {levels['support']:.2f} et {levels['resistance']:.2f}"

    risk_note = (
        "risque de consolidation à très court terme"
        if signals["flags"].get("excess_rsi")
        else "structure technique exploitable"
    )
    if signals["flags"].get("volume_spike"):
        risk_note = "volumes actifs, scénario plus crédible"

    return {
        "trend_short": trend_short,
        "trend_long": trend_long,
        "opinion": opinion,
        "targets": [levels["target_1"], levels["target_2"]],
        "risk_note": risk_note,
        "score_technical": round(score, 2),
        "premium_pct": round(premium_pct, 2),
    }
