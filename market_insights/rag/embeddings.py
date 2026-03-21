"""Vector embedding engine for RAG."""
from __future__ import annotations

import hashlib
import logging
import re
import threading
from typing import Any

import numpy as np

from market_insights.core.config import settings

_URL_RE = re.compile(r"https?://\S+")
_HTML_RE = re.compile(r"<[^>]+>")

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_model = None
_use_st = None


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
                logger.info("RAG: loaded '%s'", settings.rag_embedding_model)
                return
            except Exception as exc:
                logger.warning("RAG: sentence-transformers N/A (%s)", exc)
        from sklearn.feature_extraction.text import TfidfVectorizer

        _model = TfidfVectorizer(max_features=512, stop_words="english")
        _use_st = False
        logger.info("RAG: TF-IDF fallback")


def embed_texts(texts: list[str]) -> np.ndarray:
    _load_model()
    if _use_st:
        return _model.encode(
            texts, show_progress_bar=False, normalize_embeddings=True
        )
    return _model.fit_transform(texts).toarray().astype(np.float32)


def embed_query(query: str) -> np.ndarray:
    _load_model()
    if _use_st:
        return _model.encode(
            [query], show_progress_bar=False, normalize_embeddings=True
        )[0]
    return _model.transform([query]).toarray().astype(np.float32)[0]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = float(np.dot(a, b))
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _clean_text(text: str) -> str:
    text = _HTML_RE.sub(" ", text)
    text = _URL_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


class VectorStore:
    def __init__(self):
        self._data: dict[str, list[dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def index(self, ticker: str, chunks: list[dict]) -> int:
        if not chunks:
            return 0
        texts = [_clean_text(c["text"]) for c in chunks]
        vectors = embed_texts(texts)
        entries = []
        for i, chunk in enumerate(chunks):
            entries.append({
                "text": texts[i],
                "vector": vectors[i],
                "metadata": chunk.get("metadata", {}),
                "hash": hashlib.md5(texts[i].encode()).hexdigest()[:12],
            })
        with self._lock:
            self._data[ticker.upper()] = entries
        logger.info("Indexed %d chunks for %s", len(entries), ticker)
        return len(entries)

    def search(self, ticker: str, query: str, top_k: int = 5):
        with self._lock:
            entries = self._data.get(ticker.upper(), [])
        if not entries:
            return []
        q_vec = embed_query(query)
        scored = []
        for entry in entries:
            sim = cosine_similarity(q_vec, entry["vector"])
            scored.append({
                "text": entry["text"],
                "score": round(float(sim), 4),
                **entry["metadata"],
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def has_index(self, ticker: str) -> bool:
        return ticker.upper() in self._data

    def stats(self) -> dict:
        with self._lock:
            return {
                "tickers_indexed": list(self._data.keys()),
                "total_chunks": sum(
                    len(v) for v in self._data.values()
                ),
            }


vector_store = VectorStore()
