"""Price bar loader — remplace TOUTES les données d'un ticker."""
from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from market_insights.db.models import PriceBar


def load_price_bars(
    db: Session,
    ticker: str,
    rows: list[dict],
    source: str,
) -> int:
    """Replace ALL price bars for a ticker (any source) with one bar per date."""
    ticker = ticker.upper()

    # Annule et remplace strict: 1 seule bougie par date, la dernière valeur gagne.
    dedup_by_date: dict = {}
    for row in rows:
        date_value = row.get("date")
        if date_value is None:
            continue
        dedup_by_date[date_value] = {
            "ticker": ticker,
            "date": date_value,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
            "source": source,
        }

    db.execute(
        delete(PriceBar).where(PriceBar.ticker == ticker)
    )
    for row in sorted(dedup_by_date.values(), key=lambda x: x["date"]):
        db.add(PriceBar(**row))
    db.commit()
    return len(dedup_by_date)
