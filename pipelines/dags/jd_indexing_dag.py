"""DAG 2: JD Indexing Pipeline

Indexes unindexed job postings into pgvector.
Uses BashOperator to avoid SQLAlchemy version conflict.
"""

from datetime import timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

DEFAULT_ARGS = {
    "owner": "job-scanner",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
}

PIPELINE_CMD = "cd /opt/airflow && PYTHONPATH=/opt/airflow python -c"

with DAG(
    dag_id="jd_indexing",
    default_args=DEFAULT_ARGS,
    description="Index unindexed JDs into pgvector",
    schedule_interval="0 1 * * *",  # UTC 01:00 = KST 10:00
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["indexing", "jd", "pgvector"],
) as dag:

    index = BashOperator(
        task_id="run_indexing",
        bash_command=f"""{PIPELINE_CMD} "
from src.db.session import SessionLocal
from src.indexing.pipeline import run_incremental_index
db = SessionLocal()
while True:
    r = run_incremental_index(db, batch_size=100)
    print(r)
    if r['total_jobs'] == 0: break
db.close()
"
""",
    )
