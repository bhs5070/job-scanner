"""DAG 3: LLM Evaluation Pipeline

Evaluates unevaluated agent responses using GPT-4o as judge.
Runs daily after business hours.
"""

import logging
from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "job-scanner",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def _run_eval(**kwargs) -> dict:
    """Run batch evaluation on unevaluated records."""
    from src.db.session import SessionLocal
    from src.eval.pipeline import run_batch_eval

    db = SessionLocal()
    try:
        result = run_batch_eval(db, limit=50)
        logger.info(f"Eval result: {result}")
        return result
    finally:
        db.close()


def _log_mlflow(**kwargs) -> None:
    """Log evaluation results to MLflow."""
    from src.eval.pipeline import log_to_mlflow

    ti = kwargs["ti"]
    summary = ti.xcom_pull(task_ids="run_eval")
    if summary and summary.get("evaluated", 0) > 0:
        log_to_mlflow(summary)


with DAG(
    dag_id="llm_eval",
    default_args=DEFAULT_ARGS,
    description="Daily LLM-as-Judge evaluation of agent responses",
    schedule_interval="0 3 * * *",  # UTC 03:00 = KST 12:00
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["eval", "llm"],
) as dag:

    eval_task = PythonOperator(
        task_id="run_eval",
        python_callable=_run_eval,
    )

    mlflow_task = PythonOperator(
        task_id="log_mlflow",
        python_callable=_log_mlflow,
    )

    eval_task >> mlflow_task
