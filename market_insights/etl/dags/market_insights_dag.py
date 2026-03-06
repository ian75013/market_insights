"""DAG Airflow de démonstration.

Ce fichier est prêt à être déplacé dans un environnement Airflow réel.
"""

from datetime import datetime

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
except Exception:  # pragma: no cover
    DAG = object
    PythonOperator = object


def _extract():
    return "extract"


def _transform():
    return "transform"


def _load():
    return "load"


if DAG is not object:
    with DAG(
        dag_id="market_insights_daily",
        start_date=datetime(2025, 1, 1),
        schedule="@daily",
        catchup=False,
    ) as dag:
        extract = PythonOperator(task_id="extract_market_data", python_callable=_extract)
        transform = PythonOperator(task_id="transform_market_data", python_callable=_transform)
        load = PythonOperator(task_id="load_market_data", python_callable=_load)
        extract >> transform >> load
