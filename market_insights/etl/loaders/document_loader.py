"""Document loader — nettoie HTML et URLs avant stockage."""
from __future__ import annotations

import re

from sqlalchemy import delete
from sqlalchemy.orm import Session

from market_insights.db.models import Document

_URL_RE = re.compile(r'https?://\S+')
_HTML_RE = re.compile(r'<[^>]+>')


def _clean(text: str) -> str:
    text = _HTML_RE.sub(' ', text)
    text = _URL_RE.sub('', text)
    return re.sub(r'\s+', ' ', text).strip()


def replace_documents(db: Session, ticker: str, source: str, docs: list[dict]) -> int:
    db.execute(delete(Document).where(Document.ticker == ticker.upper(), Document.source == source))
    for doc in docs:
        db.add(Document(
            ticker=ticker.upper(),
            source=source,
            document_type=doc.get("document_type", ""),
            title=_clean(doc.get("title", "")),
            published_at=doc.get("published_at", ""),
            url=doc.get("url", ""),
            content=_clean(doc.get("content", "")),
        ))
    db.commit()
    return len(docs)
