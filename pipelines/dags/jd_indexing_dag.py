"""DAG 2: JD Indexing Pipeline

Indexes unindexed job postings into ChromaDB for RAG search.
Runs after the crawling DAG or on its own schedule.
"""

import logging
from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator, ShortCircuitOperator
from airflow.utils.dates import days_ago

logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "job-scanner",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
}


def _check_new_jds(**kwargs) -> bool:
    """Check if there are unindexed jobs. Short-circuits if none."""
    from src.db.crud.job_postings import get_unindexed_jobs
    from src.db.session import SessionLocal

    db = SessionLocal()
    try:
        jobs = get_unindexed_jobs(db, limit=1)
        has_jobs = len(jobs) > 0
        logger.info(f"Unindexed jobs exist: {has_jobs}")
        return has_jobs
    finally:
        db.close()


def _run_indexing(**kwargs) -> dict:
    """Run the incremental indexing pipeline."""
    from src.db.session import SessionLocal
    from src.indexing.pipeline import run_incremental_index

    db = SessionLocal()
    try:
        result = run_incremental_index(db, batch_size=100)
        logger.info(f"Indexing result: {result}")
        return result
    finally:
        db.close()


def _sync_deactivated(**kwargs) -> None:
    """Sync deactivated jobs from DB to ChromaDB."""
    from sqlalchemy import select

    from src.db.models import JobPosting
    from src.db.session import SessionLocal
    from src.indexing.indexer import (
        get_chroma_client,
        get_or_create_collection,
        deactivate_jobs,
    )

    db = SessionLocal()
    try:
        # Find jobs that are inactive but were indexed
        stmt = (
            select(JobPosting.id)
            .where(JobPosting.is_active.is_(False))
            .where(JobPosting.indexed_at.is_not(None))
        )
        inactive_ids = [str(row) for row in db.scalars(stmt).all()]

        if inactive_ids:
            client = get_chroma_client()
            collection = get_or_create_collection(client)
            deactivate_jobs(collection, inactive_ids)
            logger.info(f"Deactivated {len(inactive_ids)} jobs in ChromaDB")
        else:
            logger.info("No deactivated jobs to sync")
    finally:
        db.close()


with DAG(
    dag_id="jd_indexing",
    default_args=DEFAULT_ARGS,
    description="Index unindexed JDs into ChromaDB for RAG search",
    schedule_interval="0 1 * * *",  # UTC 01:00 = KST 10:00 (1hr after crawling)
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["indexing", "jd", "chromadb"],
) as dag:

    check_task = ShortCircuitOperator(
        task_id="check_new_jds",
        python_callable=_check_new_jds,
    )

    index_task = PythonOperator(
        task_id="run_indexing",
        python_callable=_run_indexing,
    )

    sync_task = PythonOperator(
        task_id="sync_deactivated",
        python_callable=_sync_deactivated,
    )

    check_task >> index_task >> sync_task
