"""Bookmark (saved jobs) API router."""

import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.routers.auth import _verify_token
from src.db.models import Bookmark, JobPosting
from src.db.session import SessionLocal

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])


def _get_user_email(auth_token: str = Cookie(default="")) -> str:
    data = _verify_token(auth_token)
    if not data:
        raise HTTPException(status_code=401, detail="Login required")
    return data["email"]


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class BookmarkRequest(BaseModel):
    job_posting_id: str


class BookmarkResponse(BaseModel):
    id: str
    job_title: str
    company: str
    source_url: str
    status: str
    created_at: str


@router.post("")
async def add_bookmark(
    req: BookmarkRequest,
    email: str = Depends(_get_user_email),
    db: Session = Depends(_get_db),
) -> dict:
    job_id = uuid.UUID(req.job_posting_id)
    # Check if already bookmarked
    existing = db.scalars(
        select(Bookmark).where(Bookmark.user_email == email, Bookmark.job_posting_id == job_id)
    ).first()
    if existing:
        return {"status": "already_saved", "id": str(existing.id)}

    bookmark = Bookmark(user_email=email, job_posting_id=job_id)
    db.add(bookmark)
    db.commit()
    return {"status": "ok", "id": str(bookmark.id)}


@router.get("")
async def list_bookmarks(
    email: str = Depends(_get_user_email),
    db: Session = Depends(_get_db),
) -> list[BookmarkResponse]:
    stmt = (
        select(Bookmark, JobPosting)
        .join(JobPosting, Bookmark.job_posting_id == JobPosting.id)
        .where(Bookmark.user_email == email)
        .order_by(Bookmark.created_at.desc())
        .limit(50)
    )
    results = db.execute(stmt).all()
    return [
        BookmarkResponse(
            id=str(bm.id),
            job_title=jp.title,
            company=jp.company,
            source_url=jp.source_url,
            status=bm.status,
            created_at=bm.created_at.isoformat(),
        )
        for bm, jp in results
    ]


@router.delete("/{bookmark_id}")
async def remove_bookmark(
    bookmark_id: str,
    email: str = Depends(_get_user_email),
    db: Session = Depends(_get_db),
) -> dict:
    bm = db.get(Bookmark, uuid.UUID(bookmark_id))
    if bm and bm.user_email == email:
        db.delete(bm)
        db.commit()
    return {"status": "ok"}
