"""Document loader — nettoie HTML et URLs avant stockage."""
from __future__ import annotations

import logging
import re

from sqlalchemy import delete
from sqlalchemy.orm import Session

from market_insights.db.models import Document

_URL_RE = re.compile(r"https?://\S+")
_HTML_RE = re.compile(r"<[^>]+>")
logger = logging.getLogger(__name__)

_MAX_TICKER_LEN = 16
_MAX_SOURCE_LEN = 64
_MAX_DOCUMENT_TYPE_LEN = 64
_MAX_TITLE_LEN = 255
_MAX_PUBLISHED_AT_LEN = 64
_MAX_URL_LEN = 512


def _clean(text: str) -> str:
    text = _HTML_RE.sub(" ", text)
    text = _URL_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def _clip(text: str, max_len: int, *, field_name: str) -> str:
    if len(text) <= max_len:
        return text
    logger.warning(
        "Truncating %s from %d to %d characters to satisfy DB schema",
        field_name,
        len(text),
        max_len,
    )
    return text[:max_len]


def replace_documents(
    db: Session, ticker: str, source: str, docs: list[dict],
) -> int:
    ticker_value = _clip(ticker.upper(), _MAX_TICKER_LEN, field_name="ticker")
    source_value = _clip(source, _MAX_SOURCE_LEN, field_name="source")

    db.execute(
        delete(Document).where(
            Document.ticker == ticker_value,
            Document.source == source_value,
        )
    )

    for doc in docs:
        document_type = _clip(
            str(doc.get("document_type", "")),
            _MAX_DOCUMENT_TYPE_LEN,
            field_name="document_type",
        )
        title = _clip(
            _clean(str(doc.get("title", ""))),
            _MAX_TITLE_LEN,
            field_name="title",
        )
        published_at = _clip(
            str(doc.get("published_at", "")),
            _MAX_PUBLISHED_AT_LEN,
            field_name="published_at",
        )
        url = _clip(
            str(doc.get("url", "")),
            _MAX_URL_LEN,
            field_name="url",
        )

        db.add(Document(
            ticker=ticker_value,
            source=source_value,
            document_type=document_type,
            title=title,
            published_at=published_at,
            url=url,
            content=_clean(str(doc.get("content", ""))),
        ))
    db.commit()
    return len(docs)
