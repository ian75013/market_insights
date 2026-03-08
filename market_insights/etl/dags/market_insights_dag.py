from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator


def extract_prices():
    print("Run ETL through application service or CLI seed script")


def refresh_rag():
    print("Refresh retrieval index / document snapshots")


with DAG(
    dag_id="market_insights_daily",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
) as dag:
    t1 = PythonOperator(task_id="extract_prices", python_callable=extract_prices)
    t2 = PythonOperator(task_id="refresh_rag", python_callable=refresh_rag)
    t1 >> t2
