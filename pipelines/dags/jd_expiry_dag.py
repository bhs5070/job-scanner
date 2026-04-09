"""DAG 4: Job Posting Expiry Detection

Checks bookmarked job posting URLs weekly.
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
    dag_id="jd_expiry_check",
    default_args=DEFAULT_ARGS,
    description="Weekly check for expired/closed job postings",
    schedule_interval="0 0 * * 0",  # Every Sunday midnight UTC
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["expiry", "jd"],
) as dag:

    check_expiry = BashOperator(
        task_id="check_and_deactivate",
        bash_command=f"""{PIPELINE_CMD} "
import requests
from sqlalchemy import select
from src.db.models import Bookmark, JobPosting
from src.db.session import SessionLocal
from src.db.crud.job_postings import deactivate_expired

db = SessionLocal()

# Check bookmarked URLs
bookmarked_ids = list(db.scalars(select(Bookmark.job_posting_id).distinct()).all())
postings = db.scalars(select(JobPosting).where(JobPosting.id.in_(bookmarked_ids), JobPosting.is_active.is_(True))).all() if bookmarked_ids else []
expired = 0
for p in postings:
    try:
        r = requests.head(p.source_url, timeout=10, allow_redirects=True, headers={{'User-Agent': 'JobScanner/1.0'}})
        if r.status_code in (404, 410, 403):
            p.is_active = False; expired += 1
    except: pass
db.commit()
print(f'URL check: {{len(postings)}} checked, {{expired}} expired')

# Deactivate old postings (90+ days)
count = deactivate_expired(db)
print(f'Old postings deactivated: {{count}}')
db.close()
"
""",
    )
