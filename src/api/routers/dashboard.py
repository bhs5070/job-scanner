"""Competitiveness dashboard API router."""

from src.api.deps import get_current_user_email, get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.db.models import Bookmark, JobPosting

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])




@router.get("/competitiveness")
async def get_competitiveness(
    skills: str = "",
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> dict:
    """Analyze how competitive the user's skills are in the market."""
    total_active = db.scalar(
        select(func.count(JobPosting.id)).where(JobPosting.is_active.is_(True))
    ) or 0

    if not skills or total_active == 0:
        return {"total_jobs": total_active, "skill_analysis": [], "matching_jobs": 0, "match_percentage": 0, "bookmark_count": 0}

    skill_list = [s.strip() for s in skills.split(",") if s.strip()]

    skill_analysis = []
    for skill in skill_list:
        count = db.scalar(
            select(func.count(JobPosting.id)).where(
                JobPosting.is_active.is_(True),
                JobPosting.description.ilike(f"%{skill}%"),
            )
        ) or 0
        pct = round(count / total_active * 100, 1) if total_active else 0
        skill_analysis.append({"skill": skill, "job_count": count, "percentage": pct})

    skill_analysis.sort(key=lambda x: x["job_count"], reverse=True)

    conditions = [JobPosting.description.ilike(f"%{s}%") for s in skill_list]
    matching = db.scalar(
        select(func.count(JobPosting.id)).where(JobPosting.is_active.is_(True), or_(*conditions))
    ) or 0

    bookmark_count = db.scalar(
        select(func.count(Bookmark.id)).where(Bookmark.user_email == email)
    ) or 0

    return {
        "total_jobs": total_active,
        "matching_jobs": matching,
        "match_percentage": round(matching / total_active * 100, 1) if total_active else 0,
        "bookmark_count": bookmark_count,
        "skill_analysis": skill_analysis,
    }
