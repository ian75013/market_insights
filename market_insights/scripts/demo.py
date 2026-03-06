from market_insights.db.bootstrap import init_db
from market_insights.db.session import SessionLocal
from market_insights.services.etl_service import run_etl
from market_insights.services.market_service import MarketInsightService


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        print(run_etl(db, "AAPL"))
        service = MarketInsightService()
        print(service.compute_fair_value(db, "AAPL"))
        print(service.generate_insight(db, "AAPL"))
    finally:
        db.close()


if __name__ == "__main__":
    main()
