from market_insights.db.bootstrap import init_db
from market_insights.db.session import SessionLocal
from market_insights.rag.store import retrieve_context
from market_insights.services.etl_service import run_etl


def test_retrieve_context_returns_documents():
    init_db()
    db = SessionLocal()
    try:
        run_etl(db, "AAPL", provider="sample")
        ctx = retrieve_context(db, "AAPL", query="growth margins services")
        assert len(ctx) >= 1
        assert "title" in ctx[0]
    finally:
        db.close()
