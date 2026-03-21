"""Tests for vector RAG store."""

from market_insights.db.bootstrap import init_db
from market_insights.db.session import SessionLocal
from market_insights.rag.store import retrieve_context, index_documents
from market_insights.services.etl_service import run_etl


def test_index_and_retrieve():
    init_db()
    db = SessionLocal()
    try:
        run_etl(db, "AAPL", provider="sample")
        count = index_documents(db, "AAPL")
        assert count > 0

        results = retrieve_context(db, "AAPL", "growth earnings revenue")
        assert len(results) >= 1
        assert "title" in results[0]
        assert "score" in results[0]
    finally:
        db.close()
