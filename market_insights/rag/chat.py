"""RAG Chat — streaming SSE + prompt nettoyé."""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Generator
from datetime import UTC, datetime

from market_insights.core.config import settings
from market_insights.llm.providers import get_llm
from market_insights.rag.store import retrieve_context

logger = logging.getLogger(__name__)

SYSTEM_FR = (
    "Tu es un analyste financier expert. Règles strictes :\n"
    "- Réponds en français, 10 phrases maximum.\n"
    "- N'écris JAMAIS d'URL, de lien, ni de chemin.\n"
    "- Cite par nom court: [Forbes], [Yahoo Finance].\n"
    "- Pas de markdown. Texte brut, paragraphes courts.\n"
    "- Reste factuel. Pas de conseil en investissement."
)
SYSTEM_EN = (
    "You are an expert financial analyst. Strict rules:\n"
    "- 10 sentences max. NEVER output URLs or links.\n"
    "- Cite sources by short name: [Forbes].\n"
    "- No markdown. Plain text, short paragraphs.\n"
    "- Stay factual. No investment advice."
)

_URL_RE = re.compile(r"https?://\S+")
_HTML_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    text = _HTML_RE.sub("", text)
    text = _URL_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def _build_prompt(ticker, question, sources):
    parts = []
    for i, s in enumerate(sources, 1):
        title = s.get("title", "Document")
        dtype = s.get("document_type", "")
        content = _clean(s.get("content", ""))
        if content:
            parts.append(f"[{i}] {title} ({dtype})\n{content}")
    ctx = "\n\n".join(parts) or "Aucun document trouvé."
    return (
        f"Ticker: {ticker}\n"
        f"Question: {question}\n\n"
        f"Documents:\n{ctx}\n\n"
        f"Réponds en citant les sources par leur nom."
    )


def _fmt_sources(sources):
    return [
        {
            "title": s.get("title", ""),
            "document_type": s.get("document_type", ""),
            "score": s.get("score", 0),
            "url": s.get("url", ""),
            "preview": _clean(s.get("content", ""))[:150],
        }
        for s in sources
    ]


# ── Standard ─────────────────────────────────────

def rag_chat(
    db, ticker, question, *,
    llm_backend=None, llm_model=None,
    language="fr", top_k=None,
):
    ticker = ticker.upper()
    top_k = top_k or settings.rag_top_k
    sources = retrieve_context(db, ticker, question, top_k=top_k)
    prompt = _build_prompt(ticker, question, sources)
    system = SYSTEM_FR if language == "fr" else SYSTEM_EN
    llm = get_llm(llm_backend)
    if llm_model:
        old = settings.llm_model
        settings.llm_model = llm_model
    try:
        if not llm.available():
            llm = get_llm("fallback")
        resp = llm.generate(prompt, system=system)
    finally:
        if llm_model:
            settings.llm_model = old
    return {
        "ticker": ticker,
        "question": question,
        "answer": _clean(resp.text),
        "sources": _fmt_sources(sources),
        "llm": {"provider": resp.provider, "model": resp.model},
        "generated_at": datetime.now(UTC).isoformat(),
    }


# ── SSE streaming ────────────────────────────────

def _sse(event, data):
    if isinstance(data, (dict, list)):
        payload = json.dumps(data, ensure_ascii=False)
    else:
        payload = data
    return f"event: {event}\ndata: {payload}\n\n"


def rag_chat_stream(
    db, ticker, question, *,
    llm_backend=None, llm_model=None,
    language="fr", top_k=None,
) -> Generator[str, None, None]:
    ticker = ticker.upper()
    top_k = top_k or settings.rag_top_k

    yield _sse("status", {
        "step": "rag_search",
        "message": "Recherche dans les documents…",
    })
    sources = retrieve_context(db, ticker, question, top_k=top_k)
    yield _sse("status", {
        "step": "rag_done",
        "message": f"{len(sources)} documents trouvés",
    })
    yield _sse("sources", _fmt_sources(sources))

    yield _sse("status", {
        "step": "prompt_build",
        "message": "Construction du prompt…",
    })
    prompt = _build_prompt(ticker, question, sources)
    system = SYSTEM_FR if language == "fr" else SYSTEM_EN

    llm = get_llm(llm_backend)
    if llm_model:
        old = settings.llm_model
        settings.llm_model = llm_model

    try:
        if not llm.available():
            llm = get_llm("fallback")
        yield _sse("status", {
            "step": "llm_start",
            "message": f"Génération ({llm.name})…",
        })

        if hasattr(llm, "generate_stream"):
            for chunk in llm.generate_stream(prompt, system=system):
                clean = _URL_RE.sub("", chunk)
                if clean:
                    yield _sse("token", {"text": clean})
        else:
            resp = llm.generate(prompt, system=system)
            for w in _clean(resp.text).split(" "):
                yield _sse("token", {"text": w + " "})

        yield _sse("status", {
            "step": "llm_done",
            "message": "Terminé",
        })
        yield _sse("done", {
            "provider": llm.name,
            "generated_at": datetime.now(UTC).isoformat(),
        })
    finally:
        if llm_model:
            settings.llm_model = old
