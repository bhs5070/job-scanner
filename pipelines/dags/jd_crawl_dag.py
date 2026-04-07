"""DAG 1: JD Crawling Pipeline

Crawls job postings from Wanted and RocketPunch daily at 09:00 KST.
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
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

SITES = ["wanted", "rocketpunch"]


def _crawl_site(site: str, **kwargs) -> dict:
    """Crawl a single site and push result to XCom."""
    from src.common.config import get_settings
    from src.crawlers import run_crawl_job

    settings = get_settings()
    result = run_crawl_job(
        site=site,
        keywords=settings.TARGET_KEYWORDS,
        max_pages=3,
    )

    logger.info(
        f"[{site}] fetched={result.total_fetched}, "
        f"parsed={result.total_parsed}, errors={len(result.errors)}"
    )

    # Return serializable data for XCom
    return {
        "site": result.site,
        "items": [item.model_dump(mode="json") for item in result.items],
        "total_fetched": result.total_fetched,
        "total_parsed": result.total_parsed,
        "errors": result.errors,
    }


def _save_to_db(**kwargs) -> dict:
    """Pull crawl results from XCom and save to DB."""
    from src.crawlers.schemas import ParsedJobPost
    from src.db.crud.crawl_logs import create_crawl_log, update_crawl_log
    from src.db.crud.job_postings import bulk_upsert_job_postings
    from src.db.session import SessionLocal

    ti = kwargs["ti"]
    dag_run = kwargs.get("dag_run")
    dag_run_id = dag_run.run_id if dag_run else ""

    db = SessionLocal()
    total_saved = 0

    try:
        for site in SITES:
            crawl_data = ti.xcom_pull(task_ids=f"crawl_{site}")
            if not crawl_data:
                continue

            log = create_crawl_log(db, source_site=site, dag_run_id=dag_run_id)

            # Parse and collect all items for bulk insert
            rows: list[dict] = []
            errors_count = 0
            for item_dict in crawl_data.get("items", []):
                try:
                    item = ParsedJobPost.model_validate(item_dict)
                    rows.append({
                        "source_site": item.source_site,
                        "source_url": item.source_url,
                        "title": item.title,
                        "company": item.company,
                        "description": item.description,
                        "requirements": item.requirements,
                        "tech_stack": item.tech_stack,
                        "posted_at": item.posted_at,
                        "collected_at": item.collected_at,
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse {item_dict.get('source_url')}: {e}")
                    errors_count += 1

            saved = bulk_upsert_job_postings(db, rows)

            update_crawl_log(
                db, log.id,
                status="success" if errors_count == 0 else "partial_fail",
                total_fetched=crawl_data.get("total_fetched", 0),
                total_saved=saved,
                error_message=f"{errors_count} items failed" if errors_count else None,
            )
            total_saved += saved
    finally:
        db.close()

    logger.info(f"Total saved to DB: {total_saved}")
    return {"total_saved": total_saved}


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

    crawl_tasks = []
    for site in SITES:
        task = PythonOperator(
            task_id=f"crawl_{site}",
            python_callable=_crawl_site,
            op_kwargs={"site": site},
        )
        crawl_tasks.append(task)

    save_task = PythonOperator(
        task_id="save_to_db",
        python_callable=_save_to_db,
    )

    crawl_tasks >> save_task
