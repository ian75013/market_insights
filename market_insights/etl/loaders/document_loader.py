from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from market_insights.db.models import Document


def replace_documents(db: Session, ticker: str, source: str, docs: list[dict]) -> int:
    db.execute(delete(Document).where(Document.ticker == ticker.upper(), Document.source == source))
    for doc in docs:
        db.add(Document(ticker=ticker.upper(), source=source, **doc))
    db.commit()
    return len(docs)
