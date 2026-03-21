from dataclasses import dataclass
import pandas as pd


@dataclass
class FairValueResult:
    fair_value: float
    confidence: float
    factors: dict


class BaselineFairValueModel:
    """Baseline explicable pour entretien.

    Idée: la "juste valeur" n'est pas présentée comme une vérité absolue,
    mais comme une estimation pilotée par momentum, risque, croissance et endettement.
    """

    def predict(
        self, df: pd.DataFrame, fundamentals: dict | None = None
    ) -> FairValueResult:
        fundamentals = fundamentals or {}
        latest = df.sort_values("date").iloc[-1]
        current_price = float(latest["close"])
        momentum = float(latest.get("momentum_20", 0.0))
        volatility = float(latest.get("volatility_20", 0.0))
        trend = float(latest.get("trend_signal", 0.0))
        rsi = float(latest.get("rsi_14", 50.0))
        revenue_growth = float(fundamentals.get("revenue_growth", 0.0))
        eps_growth = float(fundamentals.get("eps_growth", 0.0))
        debt_to_equity = float(fundamentals.get("debt_to_equity", 1.0))

        growth_boost = 1.0 + 0.20 * revenue_growth + 0.12 * eps_growth
        momentum_boost = 1.0 + 0.25 * momentum + 0.03 * trend
        risk_penalty = (
            1.0
            - min(volatility, 0.3) * 0.35
            - min(max(debt_to_equity - 1.0, 0.0), 2.0) * 0.03
        )
        rsi_penalty = 0.98 if rsi > 70 else (1.02 if rsi < 35 else 1.0)

        fair_value = (
            current_price * growth_boost * momentum_boost * rsi_penalty * risk_penalty
        )
        confidence = max(
            0.35,
            min(0.92, 0.62 + 0.12 * trend + 0.20 * revenue_growth - 0.45 * volatility),
        )

        return FairValueResult(
            fair_value=round(float(fair_value), 2),
            confidence=round(float(confidence), 2),
            factors={
                "momentum_20": round(momentum, 4),
                "volatility_20": round(volatility, 4),
                "trend_signal": int(trend),
                "rsi_14": round(rsi, 2),
                "revenue_growth": round(revenue_growth, 4),
                "eps_growth": round(eps_growth, 4),
                "debt_to_equity": round(debt_to_equity, 4),
            },
        )
