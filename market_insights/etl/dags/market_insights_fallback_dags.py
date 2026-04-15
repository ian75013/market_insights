"""Fallback DAGs for Market Insights.

This file generates:
- one manual DAG per ticker
- one manual DAG per ticker and per tab

Use them when the full morning refresh is too heavy or when Yahoo rate limits
make it necessary to relaunch in smaller slices.
"""

from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from mi_airflow_common import (
    GLOBAL_COOLDOWN_SECONDS,
    POST_RAG_COOLDOWN_SECONDS,
    TAB_COOLDOWN_SECONDS,
    TAB_ENDPOINTS,
    build_default_args,
    cooldown,
    load_tickers,
    refresh_rag_for_ticker,
    run_ticker_etl,
    warm_global_data,
    warm_tab_for_ticker,
)


def _make_ticker_etl_task(ticker: str):
    return lambda **_ctx: run_ticker_etl(ticker, log_prefix=f"[{ticker}] ")


def _make_ticker_rag_task(ticker: str):
    return lambda **_ctx: refresh_rag_for_ticker(ticker, log_prefix=f"[{ticker}] ")


def _make_global_task(ticker: str):
    return lambda **_ctx: warm_global_data(log_prefix=f"[{ticker}] ")


def _make_tab_task(ticker: str, tab_name: str):
    return lambda **_ctx: warm_tab_for_ticker(
        ticker,
        tab_name,
        log_prefix=f"[{ticker}:{tab_name}] ",
    )


def _make_cooldown_task(label: str, seconds: int, prefix: str):
    return lambda **_ctx: cooldown(label, seconds, log_prefix=prefix)


for ticker in load_tickers():
    ticker_dag_id = f"market_insights_refresh_{ticker.lower()}"

    with DAG(
        dag_id=ticker_dag_id,
        description=f"Manual fallback refresh for {ticker}",
        start_date=datetime(2026, 1, 1),
        schedule=None,
        catchup=False,
        max_active_tasks=1,
        max_active_runs=1,
        default_args=build_default_args(),
        tags=["market_insights", "fallback", "ticker", ticker.lower()],
    ) as ticker_dag:
        etl_task = PythonOperator(
            task_id=f"extract_{ticker.lower()}",
            python_callable=_make_ticker_etl_task(ticker),
        )
        rag_task = PythonOperator(
            task_id="refresh_rag",
            python_callable=_make_ticker_rag_task(ticker),
        )
        rag_gap = PythonOperator(
            task_id="cooldown_after_rag",
            python_callable=_make_cooldown_task(
                "after rag",
                POST_RAG_COOLDOWN_SECONDS,
                f"[{ticker}] ",
            ),
        )
        global_task = PythonOperator(
            task_id="warm_macro",
            python_callable=_make_global_task(ticker),
        )
        global_gap = PythonOperator(
            task_id="cooldown_after_macro",
            python_callable=_make_cooldown_task(
                "after macro",
                GLOBAL_COOLDOWN_SECONDS,
                f"[{ticker}] ",
            ),
        )

        previous_task = etl_task
        previous_task >> rag_task >> rag_gap >> global_task >> global_gap
        previous_task = global_gap

        for tab_name in TAB_ENDPOINTS:
            tab_task = PythonOperator(
                task_id=f"warm_{tab_name}",
                python_callable=_make_tab_task(ticker, tab_name),
            )
            tab_gap = PythonOperator(
                task_id=f"cooldown_after_{tab_name}",
                python_callable=_make_cooldown_task(
                    f"after {tab_name}",
                    TAB_COOLDOWN_SECONDS,
                    f"[{ticker}:{tab_name}] ",
                ),
            )
            previous_task >> tab_task >> tab_gap
            previous_task = tab_gap

    globals()[ticker_dag_id] = ticker_dag

    for tab_name in TAB_ENDPOINTS:
        tab_dag_id = f"market_insights_refresh_{ticker.lower()}_{tab_name}"
        with DAG(
            dag_id=tab_dag_id,
            description=f"Deep fallback refresh for {ticker} / {tab_name}",
            start_date=datetime(2026, 1, 1),
            schedule=None,
            catchup=False,
            max_active_tasks=1,
            max_active_runs=1,
            default_args=build_default_args(),
            tags=["market_insights", "fallback", "tab", ticker.lower(), tab_name],
        ) as tab_dag:
            etl_task = PythonOperator(
                task_id=f"extract_{ticker.lower()}",
                python_callable=_make_ticker_etl_task(ticker),
            )
            rag_task = PythonOperator(
                task_id="refresh_rag",
                python_callable=_make_ticker_rag_task(ticker),
            )
            global_task = PythonOperator(
                task_id="warm_macro",
                python_callable=_make_global_task(ticker),
            )
            global_gap = PythonOperator(
                task_id="cooldown_after_macro",
                python_callable=_make_cooldown_task(
                    "after macro",
                    GLOBAL_COOLDOWN_SECONDS,
                    f"[{ticker}:{tab_name}] ",
                ),
            )
            tab_task = PythonOperator(
                task_id=f"warm_{tab_name}",
                python_callable=_make_tab_task(ticker, tab_name),
            )
            tab_gap = PythonOperator(
                task_id=f"cooldown_after_{tab_name}",
                python_callable=_make_cooldown_task(
                    f"after {tab_name}",
                    TAB_COOLDOWN_SECONDS,
                    f"[{ticker}:{tab_name}] ",
                ),
            )

            etl_task >> rag_task >> global_task >> global_gap >> tab_task >> tab_gap

        globals()[tab_dag_id] = tab_dag
