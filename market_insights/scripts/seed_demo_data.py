"""Seed demo data for all sample tickers."""

import logging
from market_insights.db.bootstrap import init_db
from market_insights.db.session import SessionLocal
from market_insights.services.etl_service import run_etl

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

DEMO_TICKERS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "JPM",
    "JNJ",
    "BTC",
]


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        for ticker in DEMO_TICKERS:
            try:
                result = run_etl(db, ticker=ticker, provider="sample")
                logger.info(
                    "Seeded %s: %d bars, %d docs",
                    ticker,
                    result["loaded_rows"],
                    result["loaded_docs"],
                )
            except Exception as exc:
                logger.warning("Failed to seed %s: %s", ticker, exc)
    finally:
        db.close()
    logger.info("Demo seed complete for %d tickers.", len(DEMO_TICKERS))
