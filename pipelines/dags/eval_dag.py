"""DAG 3: LLM Evaluation Pipeline

Evaluates unevaluated agent responses using GPT-4o as judge.
Uses BashOperator to avoid SQLAlchemy version conflict.
"""

from datetime import timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

DEFAULT_ARGS = {
    "owner": "job-scanner",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

PIPELINE_CMD = "cd /opt/airflow && PYTHONPATH=/opt/airflow python -c"

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

    evaluate = BashOperator(
        task_id="run_eval",
        bash_command=f"""{PIPELINE_CMD} "
from src.db.session import SessionLocal
from src.eval.pipeline import run_batch_eval, log_to_mlflow
db = SessionLocal()
result = run_batch_eval(db, limit=50)
print(result)
if result['evaluated'] > 0: log_to_mlflow(result)
db.close()
"
""",
    )
