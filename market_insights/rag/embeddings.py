"""Vector embedding engine for RAG.

Uses sentence-transformers when available, falls back to TF-IDF.
Embeddings are stored in-memory (dict of numpy arrays) with SQLite metadata.
For production, swap to pgvector or Qdrant.
"""

from __future__ import annotations

import hashlib
import re

_URL_RE = re.compile(r'https?://\S+')
_HTML_RE = re.compile(r'<[^>]+>')
import logging
import threading
from typing import Any

import numpy as np

from market_insights.core.config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_model = None
_use_st = None  # will be set on first call


def _load_model():
    global _model, _use_st
    if _model is not None:
        return
    with _lock:
        if _model is not None:
            return
        if settings.rag_use_vectors:
            try:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(settings.rag_embedding_model)
                _use_st = True
                logger.info(
                    "RAG: loaded sentence-transformers model '%s'",
                    settings.rag_embedding_model,
                )
                return
            except Exception as exc:
                logger.warning(
                    "RAG: sentence-transformers unavailable (%s), "
                    "falling back to TF-IDF",
                    exc,
                )
        # TF-IDF fallback
        from sklearn.feature_extraction.text import TfidfVectorizer

        _model = TfidfVectorizer(max_features=512, stop_words="english")
        _use_st = False
        logger.info("RAG: using TF-IDF fallback embeddings")


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of texts → (N, dim) numpy array."""
    _load_model()
    if _use_st:
        return _model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    else:
        # TF-IDF: fit_transform returns sparse, convert to dense
        mat = _model.fit_transform(texts)
        return mat.toarray().astype(np.float32)


def embed_query(query: str) -> np.ndarray:
    """Embed a single query → (dim,) numpy array."""
    _load_model()
    if _use_st:
        return _model.encode(
            [query], show_progress_bar=False, normalize_embeddings=True
        )[0]
    else:
        mat = _model.transform([query])
        return mat.toarray().astype(np.float32)[0]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    dot = float(np.dot(a, b))
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ━━ In-memory vector store ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class VectorStore:
    """Simple in-memory vector store, keyed by ticker."""

    def __init__(self):
        self._data: dict[str, list[dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def index(self, ticker: str, chunks: list[dict]) -> int:
        """Index chunks for a ticker. Each chunk: {text, metadata}."""
        if not chunks:
            return 0
        texts = [c["text"] for c in chunks]
        vectors = embed_texts(texts)
        entries = []
        for i, chunk in enumerate(chunks):
            entries.append(
                {
                    "text": re.sub(r"\s+", " ", _HTML_RE.sub(" ", _URL_RE.sub("", chunk["text"]))).strip(),
                    "vector": vectors[i],
                    "metadata": chunk.get("metadata", {}),
                    "hash": hashlib.md5(chunk["text"].encode()).hexdigest()[:12],
                }
            )
        with self._lock:
            self._data[ticker.upper()] = entries
        logger.info(
            "VectorStore: indexed %d chunks for %s", len(entries), ticker.upper()
        )
        return len(entries)

    def search(self, ticker: str, query: str, top_k: int = 5) -> list[dict]:
        """Search indexed chunks by cosine similarity."""
        with self._lock:
            entries = self._data.get(ticker.upper(), [])
        if not entries:
            return []
        q_vec = embed_query(query)
        scored = []
        for entry in entries:
            sim = cosine_similarity(q_vec, entry["vector"])
            scored.append(
                {
                    "text": entry["text"],
                    "score": round(float(sim), 4),
                    **entry["metadata"],
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def has_index(self, ticker: str) -> bool:
        return ticker.upper() in self._data

    def stats(self) -> dict:
        with self._lock:
            return {
                "tickers_indexed": list(self._data.keys()),
                "total_chunks": sum(len(v) for v in self._data.values()),
            }


# Global instance
vector_store = VectorStore()
