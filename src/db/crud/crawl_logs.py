import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import CrawlLog


def create_crawl_log(
    db: Session,
    source_site: str,
    dag_run_id: str | None = None,
) -> CrawlLog:
    """Create a new crawl log entry with status 'running'."""
    log = CrawlLog(
        id=uuid.uuid4(),
        source_site=source_site,
        dag_run_id=dag_run_id,
        status="running",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def update_crawl_log(
    db: Session,
    log_id: uuid.UUID,
    *,
    status: str,
    total_fetched: int = 0,
    total_saved: int = 0,
    error_message: str | None = None,
) -> CrawlLog:
    """Update a crawl log with results."""
    log = db.get(CrawlLog, log_id)
    if log is None:
        raise ValueError(f"CrawlLog {log_id} not found")

    log.status = status
    log.total_fetched = total_fetched
    log.total_saved = total_saved
    log.error_message = error_message
    log.finished_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(log)
    return log


def get_latest_crawl_log(
    db: Session, source_site: str
) -> CrawlLog | None:
    """Get the most recent crawl log for a given site."""
    stmt = (
        select(CrawlLog)
        .where(CrawlLog.source_site == source_site)
        .order_by(CrawlLog.started_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()
