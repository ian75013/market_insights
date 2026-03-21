from market_insights.db.bootstrap import init_db
from market_insights.db.session import SessionLocal
from market_insights.services.etl_service import run_etl
from market_insights.services.market_service import MarketInsightService

if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    service = MarketInsightService()
    try:
        run_etl(db, ticker="AAPL", provider="sample")
        print(service.generate_insight(db, "AAPL"))
    finally:
        db.close()
