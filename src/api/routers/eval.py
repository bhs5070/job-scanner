"""Eval results API router."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.db.models import EvalResult

router = APIRouter(prefix="/api/eval", tags=["eval"])

METRIC_COLUMNS = [
    "relevance", "groundedness", "helpfulness",
    "faithfulness", "answer_completeness",
    "retrieval_precision", "retrieval_mrr", "context_relevance",
    "routing_accuracy",
]


@router.get("/summary")
async def get_eval_summary(db: Session = Depends(get_db)) -> dict:
    """Get evaluation summary with all 10 metrics."""
    total = db.scalar(select(func.count(EvalResult.id))) or 0

    if total == 0:
        return {"total_evaluated": 0, "metrics": {}, "by_intent": {}}

    # Average for each metric
    metrics = {}
    for col_name in METRIC_COLUMNS:
        col = getattr(EvalResult, col_name)
        avg = db.scalar(select(func.avg(col)))
        metrics[col_name] = round(float(avg), 3) if avg else None

    metrics["avg_overall"] = db.scalar(select(func.avg(EvalResult.avg_score)))
    if metrics["avg_overall"]:
        metrics["avg_overall"] = round(float(metrics["avg_overall"]), 3)

    # Average latency
    avg_latency = db.scalar(select(func.avg(EvalResult.latency_ms)))
    metrics["avg_latency_ms"] = round(float(avg_latency)) if avg_latency else None

    # By intent
    by_intent_rows = db.execute(
        select(
            EvalResult.intent,
            func.count(EvalResult.id),
            func.avg(EvalResult.avg_score),
            func.avg(EvalResult.routing_accuracy),
        ).group_by(EvalResult.intent)
    ).all()

    by_intent = {
        row[0]: {
            "count": row[1],
            "avg_score": round(float(row[2]), 3) if row[2] else 0,
            "routing_accuracy": round(float(row[3]), 3) if row[3] else 0,
        }
        for row in by_intent_rows
    }

    return {
        "total_evaluated": total,
        "metrics": metrics,
        "by_intent": by_intent,
    }


@router.get("/recent")
async def get_recent_evals(db: Session = Depends(get_db)) -> list[dict]:
    """Get recent evaluation results with all metrics."""
    stmt = select(EvalResult).order_by(EvalResult.evaluated_at.desc()).limit(20)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": str(r.id),
            "intent": r.intent,
            "query": r.query[:100],
            "relevance": r.relevance,
            "groundedness": r.groundedness,
            "helpfulness": r.helpfulness,
            "faithfulness": r.faithfulness,
            "answer_completeness": r.answer_completeness,
            "retrieval_precision": r.retrieval_precision,
            "retrieval_mrr": r.retrieval_mrr,
            "context_relevance": r.context_relevance,
            "routing_accuracy": r.routing_accuracy,
            "latency_ms": r.latency_ms,
            "avg_score": r.avg_score,
            "reasoning": r.judge_reasoning,
            "evaluated_at": r.evaluated_at.isoformat(),
        }
        for r in rows
    ]
