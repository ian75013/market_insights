"""Hybrid RAG retrieval: vector search + lexical BM25-style reranking.

Pipeline:
1. Chunk all documents for a ticker
2. Index chunks into VectorStore (sentence-transformers or TF-IDF)
3. On query: vector search → lexical rerank → return top_k with citations
"""

from __future__ import annotations

import logging
import math
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from market_insights.core.config import settings
from market_insights.db.models import Document
from market_insights.rag.chunking import chunk_text
from market_insights.rag.embeddings import vector_store

logger = logging.getLogger(__name__)

STOPWORDS = {"the", "and", "or", "de", "la", "le", "les", "des", "et", "a", "an", "of", "to", "for", "with", "is", "in", "on", "at"}


def _tokenize(text: str) -> list[str]:
    text = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return [tok for tok in text.split() if tok and tok not in STOPWORDS]


def _lexical_score(query_tokens: list[str], text: str) -> float:
    doc_tokens = _tokenize(text)
    if not doc_tokens:
        return 0.0
    c = Counter(doc_tokens)
    lexical = sum(c[t] for t in query_tokens)
    denom = math.sqrt(sum(v * v for v in c.values())) or 1.0
    return lexical / denom


def index_documents(db: Session, ticker: str) -> int:
    """Index all documents for a ticker into the vector store."""
    rows = db.execute(select(Document).where(Document.ticker == ticker.upper())).scalars().all()
    if not rows:
        return 0

    chunks = []
    for row in rows:
        for chunk in chunk_text(row.content, chunk_size=settings.rag_chunk_size, overlap=settings.rag_chunk_overlap):
            chunks.append({
                "text": chunk,
                "metadata": {
                    "title": row.title,
                    "source": row.source,
                    "document_type": row.document_type,
                    "url": row.url,
                    "published_at": row.published_at,
                },
            })

    if not chunks:
        return 0

    return vector_store.index(ticker.upper(), chunks)


def retrieve_context(db: Session, ticker: str, query: str, top_k: int | None = None) -> list[dict]:
    """Hybrid retrieval: vector search + lexical reranking."""
    top_k = top_k or settings.rag_top_k
    ticker = ticker.upper()

    # Auto-index if not yet done
    if not vector_store.has_index(ticker):
        indexed = index_documents(db, ticker)
        if indexed == 0:
            # Fallback to pure lexical if no documents
            return _pure_lexical(db, ticker, query, top_k)

    # 1. Vector search (retrieve 2x top_k for reranking)
    candidates = vector_store.search(ticker, query, top_k=top_k * 2)

    if not candidates:
        return _pure_lexical(db, ticker, query, top_k)

    # 2. Lexical rerank (hybrid score = 0.7 * vector + 0.3 * lexical)
    query_tokens = _tokenize(query + " " + ticker)
    for c in candidates:
        lex = _lexical_score(query_tokens, c["text"] + " " + c.get("title", ""))
        c["lexical_score"] = round(lex, 4)
        c["hybrid_score"] = round(0.7 * c["score"] + 0.3 * lex, 4)

    candidates.sort(key=lambda x: x["hybrid_score"], reverse=True)

    # 3. Deduplicate and format
    seen: set[str] = set()
    results: list[dict] = []
    for c in candidates:
        key = c["text"][:80]
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "title": c.get("title", ""),
            "source": c.get("source", ""),
            "document_type": c.get("document_type", ""),
            "url": c.get("url", ""),
            "published_at": c.get("published_at", ""),
            "content": c["text"],
            "score": c["hybrid_score"],
            "vector_score": c["score"],
            "lexical_score": c["lexical_score"],
        })
        if len(results) >= top_k:
            break

    return results


def _pure_lexical(db: Session, ticker: str, query: str, top_k: int) -> list[dict]:
    """Fallback lexical retrieval when vector store is empty."""
    rows = db.execute(select(Document).where(Document.ticker == ticker.upper())).scalars().all()
    if not rows:
        return []
    q = _tokenize(query + " " + ticker)
    scored: list[dict] = []
    for row in rows:
        for chunk in chunk_text(row.content, chunk_size=settings.rag_chunk_size, overlap=settings.rag_chunk_overlap):
            score = _lexical_score(q, chunk + " " + row.title)
            if score > 0:
                scored.append({
                    "title": row.title,
                    "source": row.source,
                    "document_type": row.document_type,
                    "url": row.url,
                    "published_at": row.published_at,
                    "content": chunk,
                    "score": round(score, 4),
                })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
