"""RAG Chat — streaming SSE + prompt nettoyé sans URLs."""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Generator
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from market_insights.core.config import settings
from market_insights.llm.providers import get_llm
from market_insights.rag.store import retrieve_context

logger = logging.getLogger(__name__)

SYSTEM_FR = (
    "Tu es un analyste financier expert. Règles strictes :\n"
    "- Réponds en français, 10 phrases maximum.\n"
    "- N'écris JAMAIS d'URL, de lien, ni de chemin de fichier.\n"
    "- Cite tes sources uniquement par leur nom court entre crochets, ex: [Forbes], [Yahoo Finance].\n"
    "- Pas de markdown (pas de ** ni de #). Écris en texte brut.\n"
    "- Pas de listes à puces. Rédige en paragraphes courts.\n"
    "- Reste factuel. Pas de conseil en investissement."
)
SYSTEM_EN = (
    "You are an expert financial analyst. Strict rules:\n"
    "- Answer in 10 sentences max.\n"
    "- NEVER output URLs, links, or file paths.\n"
    "- Cite sources only by short name in brackets, e.g. [Forbes], [Yahoo Finance].\n"
    "- No markdown (no ** or #). Plain text only.\n"
    "- No bullet lists. Use short paragraphs.\n"
    "- Stay factual. No investment advice."
)

_URL_RE = re.compile(r'https?://\S+')
_HTML_RE = re.compile(r'<[^>]+>')


def _clean_chunk(text: str) -> str:
    """Remove URLs and HTML from a chunk before sending to LLM."""
    text = _HTML_RE.sub('', text)
    text = _URL_RE.sub('', text)
    return re.sub(r'\s+', ' ', text).strip()


def _build_prompt(ticker: str, question: str, sources: list[dict]) -> str:
    parts = []
    for i, s in enumerate(sources, 1):
        title = s.get("title", "Document")
        dtype = s.get("document_type", "")
        content = _clean_chunk(s.get("content", ""))
        if content:
            parts.append(f"[{i}] {title} ({dtype})\n{content}")
    ctx = "\n\n".join(parts) if parts else "Aucun document pertinent trouvé."
    return f"Ticker: {ticker}\nQuestion: {question}\n\nDocuments:\n{ctx}\n\nRéponds en citant les sources par leur nom."


def _clean_response(text: str) -> str:
    """Strip any URLs that the LLM might still output."""
    text = _URL_RE.sub('', text)
    text = _HTML_RE.sub('', text)
    # Collapse multiple spaces/newlines
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ── Standard ─────────────────────────────────────────────────────

def rag_chat(db, ticker, question, *, llm_backend=None, llm_model=None, language="fr", top_k=None):
    ticker = ticker.upper()
    top_k = top_k or settings.rag_top_k
    sources = retrieve_context(db, ticker, question, top_k=top_k)
    prompt = _build_prompt(ticker, question, sources)
    system = SYSTEM_FR if language == "fr" else SYSTEM_EN
    llm = get_llm(llm_backend)
    if llm_model:
        old = settings.llm_model; settings.llm_model = llm_model
    try:
        if not llm.available(): llm = get_llm("fallback")
        resp = llm.generate(prompt, system=system)
    finally:
        if llm_model: settings.llm_model = old
    return {
        "ticker": ticker, "question": question,
        "answer": _clean_response(resp.text),
        "sources": [{"title": s.get("title",""), "document_type": s.get("document_type",""), "score": s.get("score",0)} for s in sources],
        "llm": {"provider": resp.provider, "model": resp.model},
        "generated_at": datetime.now(UTC).isoformat(),
    }


# ── Streaming SSE ────────────────────────────────────────────────

def _sse(event, data):
    payload = json.dumps(data, ensure_ascii=False) if isinstance(data, (dict, list)) else data
    return f"event: {event}\ndata: {payload}\n\n"


def rag_chat_stream(db, ticker, question, *, llm_backend=None, llm_model=None, language="fr", top_k=None) -> Generator[str, None, None]:
    ticker = ticker.upper()
    top_k = top_k or settings.rag_top_k

    yield _sse("status", {"step": "rag_search", "message": "Recherche dans les documents…"})
    sources = retrieve_context(db, ticker, question, top_k=top_k)
    yield _sse("status", {"step": "rag_done", "message": f"{len(sources)} documents trouvés"})
    yield _sse("sources", [{"title": s.get("title",""), "document_type": s.get("document_type",""), "score": s.get("score",0)} for s in sources])

    yield _sse("status", {"step": "prompt_build", "message": "Construction du prompt…"})
    prompt = _build_prompt(ticker, question, sources)
    system = SYSTEM_FR if language == "fr" else SYSTEM_EN

    llm = get_llm(llm_backend)
    if llm_model:
        old = settings.llm_model; settings.llm_model = llm_model

    try:
        if not llm.available(): llm = get_llm("fallback")
        yield _sse("status", {"step": "llm_start", "message": f"Génération ({llm.name})…"})

        if hasattr(llm, "generate_stream"):
            for chunk in llm.generate_stream(prompt, system=system):
                clean = _URL_RE.sub('', chunk)
                if clean:
                    yield _sse("token", {"text": clean})
        else:
            resp = llm.generate(prompt, system=system)
            clean = _clean_response(resp.text)
            for w in clean.split(" "):
                yield _sse("token", {"text": w + " "})

        yield _sse("status", {"step": "llm_done", "message": "Terminé"})
        yield _sse("done", {"provider": llm.name, "generated_at": datetime.now(UTC).isoformat()})
    finally:
        if llm_model: settings.llm_model = old
