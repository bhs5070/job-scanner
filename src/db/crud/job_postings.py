import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.db.models import JobPosting


def upsert_job_posting(db: Session, data: dict) -> uuid.UUID:
    """Insert or update a job posting based on source_url.

    On conflict, updates collected_at and updated_at only.
    Returns the job posting id.
    """
    stmt = insert(JobPosting).values(**data)
    stmt = stmt.on_conflict_do_update(
        index_elements=["source_url"],
        set_={
            "collected_at": stmt.excluded.collected_at,
            "updated_at": datetime.now(timezone.utc),
        },
    )
    stmt = stmt.returning(JobPosting.id)
    result = db.execute(stmt)
    db.commit()
    return result.scalar_one()


def bulk_upsert_job_postings(db: Session, items: list[dict]) -> int:
    """Upsert multiple job postings in a single statement. Returns row count."""
    if not items:
        return 0
    stmt = insert(JobPosting).values(items)
    stmt = stmt.on_conflict_do_update(
        index_elements=["source_url"],
        set_={
            "collected_at": stmt.excluded.collected_at,
            "updated_at": datetime.now(timezone.utc),
        },
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount


def get_unindexed_jobs(db: Session, limit: int = 100) -> list[JobPosting]:
    """Get active job postings that haven't been indexed yet."""
    stmt = (
        select(JobPosting)
        .where(JobPosting.is_active.is_(True))
        .where(JobPosting.indexed_at.is_(None))
        .order_by(JobPosting.collected_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def mark_as_indexed(db: Session, job_ids: list[uuid.UUID]) -> int:
    """Mark job postings as indexed."""
    stmt = (
        update(JobPosting)
        .where(JobPosting.id.in_(job_ids))
        .values(indexed_at=datetime.now(timezone.utc))
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount


def deactivate_expired(db: Session) -> int:
    """Deactivate job postings older than 90 days without updates."""
    cutoff = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    cutoff = cutoff - timedelta(days=90)

    stmt = (
        update(JobPosting)
        .where(JobPosting.is_active.is_(True))
        .where(JobPosting.updated_at < cutoff)
        .values(is_active=False)
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount


def get_job_posting_by_url(db: Session, source_url: str) -> JobPosting | None:
    """Get a single job posting by its source URL."""
    stmt = select(JobPosting).where(JobPosting.source_url == source_url)
    return db.scalars(stmt).first()
