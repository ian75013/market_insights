from sqlalchemy import delete
from sqlalchemy.orm import Session

from market_insights.db.models import PriceBar


def load_price_bars(db: Session, ticker: str, rows: list[dict]) -> int:
    db.execute(delete(PriceBar).where(PriceBar.ticker == ticker))
    for row in rows:
        db.add(PriceBar(**row))
    db.commit()
    return len(rows)
