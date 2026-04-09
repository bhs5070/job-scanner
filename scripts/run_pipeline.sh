#!/bin/bash
# Job Scanner Pipeline Runner
# Run this manually or via cron as an alternative to Airflow
#
# Usage:
#   ./scripts/run_pipeline.sh crawl    # Run crawling
#   ./scripts/run_pipeline.sh index    # Run indexing
#   ./scripts/run_pipeline.sh eval     # Run LLM eval
#   ./scripts/run_pipeline.sh all      # Run all pipelines

set -e
cd "$(dirname "$0")/.."
export PYTHONPATH=.

case "${1:-all}" in
  crawl)
    echo "[1/1] Running crawling pipeline..."
    python -c "
from src.crawlers import run_crawl_job
from src.db.crud.job_postings import bulk_upsert_job_postings
from src.db.session import SessionLocal
from src.db.models import JobPosting
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timezone
db = SessionLocal()
for site in ['wanted', 'saramin']:
    result = run_crawl_job(site=site, keywords=['AI Engineer', 'ML Engineer', 'FDSE', '백엔드', '신입'], max_pages=2)
    rows = [{'source_site': i.source_site, 'source_url': i.source_url, 'title': i.title,
             'company': i.company, 'description': i.description, 'requirements': i.requirements,
             'tech_stack': i.tech_stack, 'collected_at': i.collected_at} for i in result.items]
    if rows:
        stmt = insert(JobPosting).values(rows)
        stmt = stmt.on_conflict_do_update(index_elements=['source_url'],
            set_={'collected_at': stmt.excluded.collected_at, 'updated_at': datetime.now(timezone.utc)})
        db.execute(stmt); db.commit()
    print(f'{site}: {result.total_parsed}건')
db.close()
"
    ;;
  index)
    echo "[1/1] Running indexing pipeline..."
    python -c "
from src.db.session import SessionLocal
from src.indexing.pipeline import run_incremental_index
db = SessionLocal()
while True:
    r = run_incremental_index(db, batch_size=100)
    print(r)
    if r['total_jobs'] == 0: break
db.close()
"
    ;;
  eval)
    echo "[1/1] Running eval pipeline..."
    python -c "
from src.db.session import SessionLocal
from src.eval.pipeline import run_batch_eval, log_to_mlflow
db = SessionLocal()
result = run_batch_eval(db, limit=50)
print(result)
if result['evaluated'] > 0: log_to_mlflow(result)
db.close()
"
    ;;
  all)
    echo "=== Running all pipelines ==="
    $0 crawl
    $0 index
    $0 eval
    echo "=== All done ==="
    ;;
  *)
    echo "Usage: $0 {crawl|index|eval|all}"
    exit 1
    ;;
esac
