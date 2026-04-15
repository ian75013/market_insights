from __future__ import annotations

import logging
import os
import sys
import time
from datetime import timedelta

import httpx

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

logger = logging.getLogger(__name__)

CRYPTO_TICKERS: set[str] = {
    "BTC", "ETH", "SOL", "ADA", "DOGE", "DOT", "AVAX",
    "MATIC", "LINK", "UNI", "XRP", "BNB", "ATOM", "LTC", "NEAR",
}

DEFAULT_TICKERS: list[str] = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM", "JNJ", "BTC",
]

MI_API_BASE = os.getenv("MI_API_BASE", "http://mi-api:8000")
FULL_REFRESH_SCHEDULE = os.getenv("MI_FULL_REFRESH_SCHEDULE", "0 5 * * *")
AIRFLOW_RETRIES = int(os.getenv("MI_AIRFLOW_RETRIES", "7"))
AIRFLOW_RETRY_DELAY_HOURS = int(os.getenv("MI_AIRFLOW_RETRY_DELAY_HOURS", "1"))
STOCK_ETL_COOLDOWN_SECONDS = int(os.getenv("MI_STOCK_ETL_COOLDOWN_SECONDS", "420"))
CRYPTO_ETL_COOLDOWN_SECONDS = int(os.getenv("MI_CRYPTO_ETL_COOLDOWN_SECONDS", "120"))
POST_RAG_COOLDOWN_SECONDS = int(os.getenv("MI_POST_RAG_COOLDOWN_SECONDS", "45"))
TAB_COOLDOWN_SECONDS = int(os.getenv("MI_TAB_COOLDOWN_SECONDS", "30"))
GLOBAL_COOLDOWN_SECONDS = int(os.getenv("MI_GLOBAL_COOLDOWN_SECONDS", "30"))

GLOBAL_ENDPOINTS: list[tuple[str, str]] = [
    ("macro", "/macro"),
]

TAB_ENDPOINTS: dict[str, list[tuple[str, str]]] = {
    "overview": [
        ("fair_value", "/fair-value/{ticker}"),
        ("insight", "/insights/{ticker}"),
        ("hybrid", "/insights/{ticker}/hybrid"),
    ],
    "technique": [
        ("comparable", "/insights/{ticker}/comparable"),
    ],
    "fondamentaux": [
        ("fundamentals", "/fundamentals/{ticker}"),
        ("fair_value", "/fair-value/{ticker}"),
    ],
    "news": [
        ("news", "/news/{ticker}?limit=10"),
    ],
}


def build_default_args() -> dict:
    return {
        "owner": "market_insights",
        "depends_on_past": False,
        "retries": AIRFLOW_RETRIES,
        "retry_delay": timedelta(hours=AIRFLOW_RETRY_DELAY_HOURS),
        "email_on_failure": False,
    }


def load_tickers() -> list[str]:
    raw = os.getenv("MI_TICKERS") or os.getenv("TICKERS")
    if not raw:
        return DEFAULT_TICKERS

    tickers: list[str] = []
    for item in raw.split(","):
        ticker = item.strip().upper()
        if ticker and ticker not in tickers:
            tickers.append(ticker)
    return tickers or DEFAULT_TICKERS


def provider_for_ticker(ticker: str) -> str:
    return (
        "coingecko"
        if ticker.upper() in CRYPTO_TICKERS
        else os.getenv("MI_STOCK_PROVIDER", "yahoo")
    )


def etl_cooldown_for_ticker(ticker: str) -> int:
    return (
        CRYPTO_ETL_COOLDOWN_SECONDS
        if ticker.upper() in CRYPTO_TICKERS
        else STOCK_ETL_COOLDOWN_SECONDS
    )


def session_factory():
    db_url = os.getenv("MI_DATABASE_URL")
    if db_url:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(db_url, future=True)
        return sessionmaker(bind=engine)

    from market_insights.db.session import SessionLocal

    return SessionLocal


def run_ticker_etl(ticker: str, log_prefix: str = "[AIRFLOW]") -> dict:
    from market_insights.services.etl_service import run_etl

    provider = provider_for_ticker(ticker)
    logger.info("%s[ETL] Starting %s via %s", log_prefix, ticker, provider)
    Session = session_factory()
    db = Session()
    try:
        result = run_etl(db, ticker=ticker, provider=provider)
        logger.info("%s[ETL] Done %s — %s", log_prefix, ticker, result)
        return result
    finally:
        db.close()


def _call_api(path: str, method: str = "GET") -> None:
    url = f"{MI_API_BASE}{path}"
    with httpx.Client(timeout=120) as client:
        response = client.request(method, url)
        response.raise_for_status()


def refresh_rag_for_ticker(ticker: str, log_prefix: str = "[AIRFLOW]") -> None:
    path = f"/rag/index/{ticker}"
    _call_api(path, method="POST")
    logger.info("%s[RAG] Reindexed %s", log_prefix, ticker)


def warm_global_data(log_prefix: str = "[AIRFLOW]") -> None:
    for endpoint_name, path in GLOBAL_ENDPOINTS:
        _call_api(path)
        logger.info("%s[GLOBAL] Warmed %s", log_prefix, endpoint_name)


def warm_tab_for_ticker(
    ticker: str,
    tab_name: str,
    log_prefix: str = "[AIRFLOW]",
) -> None:
    endpoints = TAB_ENDPOINTS[tab_name]
    for endpoint_name, template in endpoints:
        _call_api(template.format(ticker=ticker))
        logger.info("%s[TAB] Warmed %s for %s", log_prefix, endpoint_name, ticker)


def cooldown(label: str, seconds: int, log_prefix: str = "[AIRFLOW]") -> None:
    if seconds <= 0:
        logger.info("%s[COOLDOWN] Skipped %s", log_prefix, label)
        return

    logger.info("%s[COOLDOWN] %s for %ss", log_prefix, label, seconds)
    time.sleep(seconds)
