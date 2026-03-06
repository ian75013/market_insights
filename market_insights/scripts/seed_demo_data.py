from market_insights.db.bootstrap import init_db
from market_insights.db.session import SessionLocal
from market_insights.services.etl_service import run_etl


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        for ticker in ["AAPL", "MSFT", "NVDA"]:
            run_etl(db, ticker=ticker, provider="sample")
    finally:
        db.close()
