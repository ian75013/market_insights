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
    """Replace ALL price bars for a ticker (any source)."""
    db.execute(
        delete(PriceBar).where(PriceBar.ticker == ticker.upper())
    )
    for row in rows:
        db.add(PriceBar(**row, source=source))
    db.commit()
    return len(rows)
