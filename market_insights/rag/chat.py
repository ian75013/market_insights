"""RAG Chat service — Retrieval-Augmented Generation for financial Q&A.

Pipeline:
1. Retrieve top-k relevant chunks from vector store
2. Build prompt with context
3. Send to selected LLM provider
4. Return response with cited sources
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from market_insights.core.config import settings
from market_insights.llm.providers import get_llm, LLMResponse
from market_insights.rag.store import retrieve_context

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_FR = """Tu es un analyste financier expert spécialisé dans la recherche actions.
Tu réponds en français de manière structurée et factuelle.
Tu cites tes sources en les référençant par [Source: titre].
Tu ne donnes jamais de conseil en investissement personnalisé.
Si les documents fournis ne contiennent pas assez d'information, dis-le clairement."""

SYSTEM_PROMPT_EN = """You are an expert financial analyst specialized in equity research.
You answer in a structured, factual manner.
You cite sources by referencing them as [Source: title].
You never give personalized investment advice.
If the provided documents lack sufficient information, state it clearly."""


def rag_chat(
    db: Session,
    ticker: str,
    question: str,
    *,
    llm_backend: str | None = None,
    llm_model: str | None = None,
    language: str = "fr",
    top_k: int | None = None,
) -> dict:
    """RAG-powered chat: retrieve context → augment prompt → generate."""
    ticker = ticker.upper()
    top_k = top_k or settings.rag_top_k

    # 1. Retrieve
    sources = retrieve_context(db, ticker, question, top_k=top_k)

    # 2. Build context block
    context_parts = []
    for i, src in enumerate(sources, 1):
        context_parts.append(
            f"[{i}] {src.get('title', 'Document')} ({src.get('document_type', '')}) "
            f"— score: {src.get('score', 0)}\n{src.get('content', '')}"
        )
    context_block = "\n\n".join(context_parts) if context_parts else "Aucun document pertinent trouvé."

    # 3. Augmented prompt
    prompt = f"""Ticker: {ticker}
Question: {question}

Documents de contexte:
{context_block}

Réponds à la question en te basant sur les documents ci-dessus. Cite les sources pertinentes."""

    # 4. Generate
    system = SYSTEM_PROMPT_FR if language == "fr" else SYSTEM_PROMPT_EN
    llm = get_llm(llm_backend)

    # Override model if specified
    if llm_model:
        original_model = settings.llm_model
        settings.llm_model = llm_model

    try:
        if not llm.available():
            llm = get_llm("fallback")

        response: LLMResponse = llm.generate(prompt, system=system)
    finally:
        if llm_model:
            settings.llm_model = original_model

    return {
        "ticker": ticker,
        "question": question,
        "answer": response.text,
        "sources": [
            {
                "title": s.get("title", ""),
                "document_type": s.get("document_type", ""),
                "score": s.get("score", 0),
                "content_preview": (s.get("content", ""))[:200],
            }
            for s in sources
        ],
        "llm": {
            "provider": response.provider,
            "model": response.model,
            "usage": response.usage,
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }
