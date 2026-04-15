"""Market Insights — full site refresh DAG.

Scheduled DAG intended for the daily morning refresh on the VPS.

Flow
----
1. Run ETL for every configured ticker.
2. Rebuild RAG indexes for every ticker.
3. Warm the API endpoints consumed by the site so overview, charts,
   fundamentals, news, hybrid insights, and macro data are immediately ready.

Tickers are read from MI_TICKERS or TICKERS if present, otherwise the default
dashboard set is used.

Retries are hourly. By default the DAG attempts once plus 7 retries.
"""

from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

from mi_airflow_common import (
    FULL_REFRESH_SCHEDULE,
    GLOBAL_COOLDOWN_SECONDS,
    POST_RAG_COOLDOWN_SECONDS,
    TAB_COOLDOWN_SECONDS,
    TAB_ENDPOINTS,
    build_default_args,
    cooldown,
    etl_cooldown_for_ticker,
    load_tickers,
    refresh_rag_for_ticker,
    run_ticker_etl,
    warm_global_data,
    warm_tab_for_ticker,
)

_TICKERS = load_tickers()


def _make_etl_task(ticker: str):
    return lambda **_ctx: run_ticker_etl(ticker, log_prefix="[FULL-REFRESH] ")


def _make_rag_task(ticker: str):
    return lambda **_ctx: refresh_rag_for_ticker(ticker, log_prefix="[FULL-REFRESH] ")


def _make_tab_task(ticker: str, tab_name: str):
    return lambda **_ctx: warm_tab_for_ticker(
        ticker,
        tab_name,
        log_prefix="[FULL-REFRESH] ",
    )


def _make_cooldown_task(label: str, seconds: int):
    return lambda **_ctx: cooldown(label, seconds, log_prefix="[FULL-REFRESH] ")


def _warm_global(**_ctx) -> None:
    warm_global_data(log_prefix="[FULL-REFRESH] ")


with DAG(
    dag_id="market_insights_full_refresh",
    description="Daily morning full refresh for all dashboard tickers and site data",
    start_date=datetime(2026, 1, 1),
    schedule=FULL_REFRESH_SCHEDULE,
    catchup=False,
    max_active_tasks=1,
    max_active_runs=1,
    default_args=build_default_args(),
    tags=["market_insights", "etl", "ops", "full-refresh", "scheduled"],
) as dag:

    start_task = EmptyOperator(task_id="start_refresh")

    warm_global_task = PythonOperator(
        task_id="warm_macro",
        python_callable=_warm_global,
    )
    end_macro_task = PythonOperator(
        task_id="warm_macro_final",
        python_callable=_warm_global,
    )

    previous_task = start_task
    previous_task >> warm_global_task
    previous_task = warm_global_task

    for ticker in _TICKERS:
        etl_gap = PythonOperator(
            task_id=f"cooldown_before_extract_{ticker.lower()}",
            python_callable=_make_cooldown_task(
                f"before extract {ticker}",
                etl_cooldown_for_ticker(ticker),
            ),
        )
        extract_task = PythonOperator(
            task_id=f"extract_{ticker.lower()}",
            python_callable=_make_etl_task(ticker),
        )
        rag_task = PythonOperator(
            task_id=f"refresh_rag_{ticker.lower()}",
            python_callable=_make_rag_task(ticker),
        )
        post_rag_gap = PythonOperator(
            task_id=f"cooldown_after_rag_{ticker.lower()}",
            python_callable=_make_cooldown_task(
                f"after rag {ticker}",
                POST_RAG_COOLDOWN_SECONDS,
            ),
        )

        previous_task >> etl_gap >> extract_task >> rag_task >> post_rag_gap
        previous_task = post_rag_gap

        for tab_name in TAB_ENDPOINTS:
            tab_task = PythonOperator(
                task_id=f"warm_{ticker.lower()}_{tab_name}",
                python_callable=_make_tab_task(ticker, tab_name),
            )
            tab_gap = PythonOperator(
                task_id=f"cooldown_after_{ticker.lower()}_{tab_name}",
                python_callable=_make_cooldown_task(
                    f"after {ticker} {tab_name}",
                    TAB_COOLDOWN_SECONDS,
                ),
            )
            previous_task >> tab_task >> tab_gap
            previous_task = tab_gap

    final_gap = PythonOperator(
        task_id="cooldown_before_macro_final",
        python_callable=_make_cooldown_task(
            "before final macro",
            GLOBAL_COOLDOWN_SECONDS,
        ),
    )

    previous_task >> final_gap >> end_macro_task
