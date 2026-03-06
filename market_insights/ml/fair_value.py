from dataclasses import dataclass
import pandas as pd


@dataclass
class FairValueResult:
    fair_value: float
    confidence: float
    factors: dict


class BaselineFairValueModel:
    """Modèle de juste valeur simple mais explicable pour entretien."""

    def predict(self, df: pd.DataFrame) -> FairValueResult:
        latest = df.sort_values("date").iloc[-1]
        current_price = float(latest["close"])
        momentum = float(latest.get("momentum_20", 0.0))
        volatility = float(latest.get("volatility_20", 0.0))
        trend = float(latest.get("trend_signal", 0.0))
        rsi = float(latest.get("rsi_14", 50.0))

        value_adjustment = 1.0 + (0.25 * momentum) + (0.03 * trend)
        risk_penalty = 1.0 - min(volatility, 0.3) * 0.35
        rsi_penalty = 0.98 if rsi > 70 else (1.02 if rsi < 35 else 1.0)

        fair_value = current_price * value_adjustment * risk_penalty * rsi_penalty
        confidence = max(0.35, min(0.9, 0.65 + 0.15 * trend - 0.5 * volatility))

        return FairValueResult(
            fair_value=round(float(fair_value), 2),
            confidence=round(float(confidence), 2),
            factors={
                "momentum_20": round(momentum, 4),
                "volatility_20": round(volatility, 4),
                "trend_signal": int(trend),
                "rsi_14": round(rsi, 2),
            },
        )
