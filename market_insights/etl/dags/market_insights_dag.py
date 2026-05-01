"""Market Insights — daily ETL DAG.

Schedule: every day at 00:30 UTC (markets have closed globally by then).

Pipeline per ticker
-------------------
1. extract_and_load_<TICKER>
    Calls run_etl(db, ticker, provider) — the same function used by the API.
    Stocks → Yahoo Finance.  Crypto → CoinGecko.
    On failure the task retries up to 3 times with a 5-minute delay.

2. refresh_rag
    Triggers /rag/index for every ticker via the internal API so the vector
    store reflects fresh fundamentals and news.
    Runs *after* all extract tasks succeed (downstream dependency).

Parallelism
-----------
All extract tasks run in parallel (LocalExecutor, max_active_tasks=4).
refresh_rag waits for all of them before running.

Configuration
-------------
The DAG reads MI_DATABASE_URL and MI_USE_NETWORK from the Airflow environment
(set in docker-compose.airflow.yml via the x-airflow-common block).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import httpx

from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

# ── Tickers & routing ─────────────────────────────────────────────────────────
_CRYPTO: set[str] = {
    "BTC", "ETH", "SOL", "ADA", "DOGE", "DOT", "AVAX",
    "MATIC", "LINK", "UNI", "XRP", "BNB", "ATOM", "LTC", "NEAR",
}
_TICKERS: list[str] = [
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

_MI_API_BASE = os.getenv("MI_API_BASE", "http://mi-api:8000")

# ── Default DAG args ──────────────────────────────────────────────────────────
_DEFAULT_ARGS = {
    "owner": "market_insights",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


# ── Task callables ────────────────────────────────────────────────────────────

def _etl_ticker(ticker: str, **_ctx) -> dict:
    """Extract + load a single ticker via the market-insights API."""
    provider = "coingecko" if ticker in _CRYPTO else "yahoo"
    logger.info("[ETL] Starting %s via %s", ticker, provider)
    url = f"{_MI_API_BASE}/etl/run"
    with httpx.Client(timeout=300) as client:
        r = client.post(url, params={"ticker": ticker, "provider": provider})
        r.raise_for_status()
    result = r.json()
    logger.info("[ETL] Done %s — %s", ticker, result)
    return result


def _refresh_rag(**_ctx) -> None:
    """POST /rag/index/<ticker> for every ticker to rebuild vector store."""
    for ticker in _TICKERS:
        url = f"{_MI_API_BASE}/rag/index/{ticker}"
        try:
            r = httpx.post(url, timeout=120)
            r.raise_for_status()
            logger.info("[RAG] Reindexed %s", ticker)
        except Exception as exc:
            # Log but don't fail the whole task — RAG is best-effort
            logger.warning("[RAG] Index failed for %s: %s", ticker, exc)


# ── DAG definition ────────────────────────────────────────────────────────────

with DAG(
    dag_id="market_insights_daily",
    description=(
        "Daily ETL: prices + fundamentals + news for all tickers, "
        "then RAG refresh"
    ),
    start_date=datetime(2026, 1, 1),
    schedule="30 0 * * *",   # 00:30 UTC every day
    catchup=False,
    max_active_tasks=4,       # run up to 4 extract tasks in parallel
    default_args=_DEFAULT_ARGS,
    tags=["market_insights", "etl", "daily"],
) as dag:

    extract_tasks = [
        PythonOperator(
            task_id=f"extract_{ticker.lower()}",
            python_callable=_etl_ticker,
            op_kwargs={"ticker": ticker},
        )
        for ticker in _TICKERS
    ]

    rag_task = PythonOperator(
        task_id="refresh_rag",
        python_callable=_refresh_rag,
    )

    # All extracts must succeed before RAG refresh
    extract_tasks >> rag_task


