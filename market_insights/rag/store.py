from __future__ import annotations

from collections import Counter
import math
from sqlalchemy import select
from sqlalchemy.orm import Session

from market_insights.db.models import Document
from market_insights.rag.chunking import chunk_text


STOPWORDS = {"the", "and", "or", "de", "la", "le", "les", "des", "et", "a", "an", "of", "to", "for", "with"}


def _tokenize(text: str) -> list[str]:
    text = ''.join(ch.lower() if ch.isalnum() else ' ' for ch in text)
    return [tok for tok in text.split() if tok and tok not in STOPWORDS]


def _score(query_tokens: list[str], text: str) -> float:
    doc_tokens = _tokenize(text)
    if not doc_tokens:
        return 0.0
    c = Counter(doc_tokens)
    lexical = sum(c[t] for t in query_tokens)
    denom = math.sqrt(sum(v * v for v in c.values())) or 1.0
    return lexical / denom


def retrieve_context(db: Session, ticker: str, query: str, top_k: int = 5) -> list[dict]:
    rows = db.execute(select(Document).where(Document.ticker == ticker.upper())).scalars().all()
    if not rows:
        return []
    q = _tokenize(query + ' ' + ticker)
    scored: list[dict] = []
    for row in rows:
        for chunk in chunk_text(row.content):
            score = _score(q, chunk + ' ' + row.title)
            if score > 0:
                scored.append({
                    'title': row.title,
                    'source': row.source,
                    'document_type': row.document_type,
                    'url': row.url,
                    'published_at': row.published_at,
                    'content': chunk,
                    'score': round(score, 4),
                })
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:top_k]
