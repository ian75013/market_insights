"""Macro metrics loader — annule et remplace le snapshot macro."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from market_insights.db.models import MacroMetric


def replace_macro_metrics(db: Session, metrics: dict[str, float], source: str) -> int:
    """Replace the macro snapshot table with the provided metrics."""
    snapshot = []
    for key, value in metrics.items():
        try:
            snapshot.append(
                {
                    "metric_key": str(key),
                    "metric_value": float(value),
                    "source": source,
                    "updated_at": datetime.now(UTC),
                }
            )
        except (TypeError, ValueError):
            continue

    db.execute(delete(MacroMetric))
    for row in snapshot:
        db.add(MacroMetric(**row))
    db.commit()
    return len(snapshot)
