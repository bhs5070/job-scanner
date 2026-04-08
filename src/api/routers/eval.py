"""Eval results API router."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.deps import get_current_user_email, get_db
from src.db.models import EvalResult

router = APIRouter(prefix="/api/eval", tags=["eval"])


@router.get("/summary")
async def get_eval_summary(
    db: Session = Depends(get_db),
) -> dict:
    """Get evaluation summary statistics."""
    total = db.scalar(select(func.count(EvalResult.id))) or 0

    if total == 0:
        return {
            "total_evaluated": 0,
            "avg_relevance": None,
            "avg_groundedness": None,
            "avg_helpfulness": None,
            "avg_overall": None,
            "by_intent": {},
        }

    avg_rel = db.scalar(select(func.avg(EvalResult.relevance))) or 0
    avg_grd = db.scalar(select(func.avg(EvalResult.groundedness))) or 0
    avg_hlp = db.scalar(select(func.avg(EvalResult.helpfulness))) or 0
    avg_all = db.scalar(select(func.avg(EvalResult.avg_score))) or 0

    # By intent
    by_intent_rows = db.execute(
        select(
            EvalResult.intent,
            func.count(EvalResult.id),
            func.avg(EvalResult.avg_score),
        )
        .group_by(EvalResult.intent)
    ).all()

    by_intent = {
        row[0]: {"count": row[1], "avg_score": round(float(row[2]), 3) if row[2] else 0}
        for row in by_intent_rows
    }

    return {
        "total_evaluated": total,
        "avg_relevance": round(float(avg_rel), 3),
        "avg_groundedness": round(float(avg_grd), 3),
        "avg_helpfulness": round(float(avg_hlp), 3),
        "avg_overall": round(float(avg_all), 3),
        "by_intent": by_intent,
    }


@router.get("/recent")
async def get_recent_evals(
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get recent evaluation results."""
    stmt = (
        select(EvalResult)
        .order_by(EvalResult.evaluated_at.desc())
        .limit(20)
    )
    rows = db.scalars(stmt).all()
    return [
        {
            "id": str(r.id),
            "intent": r.intent,
            "query": r.query[:100],
            "relevance": r.relevance,
            "groundedness": r.groundedness,
            "helpfulness": r.helpfulness,
            "avg_score": r.avg_score,
            "reasoning": r.judge_reasoning,
            "evaluated_at": r.evaluated_at.isoformat(),
        }
        for r in rows
    ]
