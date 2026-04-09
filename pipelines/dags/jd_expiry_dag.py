"""DAG 4: Job Posting Expiry Detection

Checks bookmarked job posting URLs weekly.
Marks expired/closed postings as inactive.
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


def _check_expired_postings(**kwargs) -> dict:
    """Check bookmarked job posting URLs for expiry."""
    import requests
    from sqlalchemy import select, update

    from src.db.models import Bookmark, JobPosting
    from src.db.session import SessionLocal

    db = SessionLocal()
    expired_count = 0

    try:
        # Get all bookmarked job posting IDs
        bookmarked_ids = db.scalars(
            select(Bookmark.job_posting_id).distinct()
        ).all()

        if not bookmarked_ids:
            logger.info("No bookmarked postings to check.")
            return {"checked": 0, "expired": 0}

        # Check each posting's URL
        postings = db.scalars(
            select(JobPosting).where(
                JobPosting.id.in_(bookmarked_ids),
                JobPosting.is_active.is_(True),
            )
        ).all()

        for posting in postings:
            try:
                resp = requests.head(
                    posting.source_url, timeout=10, allow_redirects=True,
                    headers={"User-Agent": "JobScanner/1.0"},
                )
                if resp.status_code in (404, 410, 403):
                    posting.is_active = False
                    expired_count += 1
                    logger.info(f"Expired: {posting.title} ({posting.source_url})")
            except requests.RequestException:
                # Connection error — might be temporary, skip
                pass

        db.commit()
        logger.info(f"Checked {len(postings)}, expired: {expired_count}")
        return {"checked": len(postings), "expired": expired_count}

    finally:
        db.close()


def _deactivate_old_postings(**kwargs) -> dict:
    """Deactivate postings older than 90 days without updates."""
    from src.db.crud.job_postings import deactivate_expired
    from src.db.session import SessionLocal

    db = SessionLocal()
    try:
        count = deactivate_expired(db)
        logger.info(f"Deactivated {count} old postings (90+ days)")
        return {"deactivated": count}
    finally:
        db.close()


with DAG(
    dag_id="jd_expiry_check",
    default_args=DEFAULT_ARGS,
    description="Weekly check for expired/closed job postings",
    schedule_interval="0 0 * * 0",  # Every Sunday midnight UTC
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["expiry", "jd"],
) as dag:

    check_task = PythonOperator(
        task_id="check_expired_postings",
        python_callable=_check_expired_postings,
    )

    deactivate_task = PythonOperator(
        task_id="deactivate_old_postings",
        python_callable=_deactivate_old_postings,
    )

    check_task >> deactivate_task
