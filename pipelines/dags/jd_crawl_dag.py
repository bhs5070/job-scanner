"""DAG 1: JD Crawling Pipeline

Crawls job postings from Wanted and Saramin daily at 09:00 KST.
Uses BashOperator to avoid SQLAlchemy version conflict with Airflow.
"""

from datetime import timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

DEFAULT_ARGS = {
    "owner": "job-scanner",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

PIPELINE_CMD = "cd /opt/airflow && PYTHONPATH=/opt/airflow python -c"

with DAG(
    dag_id="jd_crawling",
    default_args=DEFAULT_ARGS,
    description="Daily JD crawling from job platforms",
    schedule_interval="0 0 * * *",  # UTC 00:00 = KST 09:00
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["crawling", "jd"],
) as dag:

    crawl = BashOperator(
        task_id="crawl_and_save",
        bash_command=f"""{PIPELINE_CMD} "
from src.crawlers import run_crawl_job
from src.db.session import SessionLocal
from src.db.models import JobPosting
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timezone
db = SessionLocal()
for site in ['wanted', 'saramin']:
    result = run_crawl_job(site=site, keywords=['AI Engineer', 'ML Engineer', 'FDSE'], max_pages=2)
    rows = [{{'source_site': i.source_site, 'source_url': i.source_url, 'title': i.title,
             'company': i.company, 'description': i.description, 'requirements': i.requirements,
             'tech_stack': i.tech_stack, 'collected_at': i.collected_at}} for i in result.items]
    if rows:
        stmt = insert(JobPosting).values(rows)
        stmt = stmt.on_conflict_do_update(index_elements=['source_url'],
            set_={{'collected_at': stmt.excluded.collected_at, 'updated_at': datetime.now(timezone.utc)}})
        db.execute(stmt); db.commit()
    print(f'{{site}}: {{result.total_parsed}}건')
db.close()
"
""",
    )
