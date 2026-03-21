from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from market_insights.db.models import PriceBar


def load_price_bars(db: Session, ticker: str, rows: list[dict], source: str) -> int:
    db.execute(delete(PriceBar).where(PriceBar.ticker == ticker.upper(), PriceBar.source == source))
    for row in rows:
        db.add(PriceBar(**row, source=source))
    db.commit()
    return len(rows)
