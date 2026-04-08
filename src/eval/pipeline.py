"""Batch evaluation pipeline: evaluate unevaluated match_history records."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import EvalResult, MatchHistory
from src.eval.metrics.judge import evaluate_response

logger = logging.getLogger(__name__)


def run_batch_eval(db: Session, limit: int = 50) -> dict:
    """Evaluate match_history records that haven't been evaluated yet.

    Returns summary of evaluation results.
    """
    # Find unevaluated records
    evaluated_ids = select(EvalResult.match_history_id).where(
        EvalResult.match_history_id.is_not(None)
    )
    stmt = (
        select(MatchHistory)
        .where(MatchHistory.id.not_in(evaluated_ids))
        .order_by(MatchHistory.created_at.desc())
        .limit(limit)
    )
    records = db.scalars(stmt).all()

    if not records:
        logger.info("No unevaluated records found.")
        return {"evaluated": 0, "skipped": 0}

    logger.info(f"Evaluating {len(records)} records...")

    evaluated = 0
    skipped = 0
    total_scores = {"relevance": 0, "groundedness": 0, "helpfulness": 0}

    for record in records:
        # Build context from results JSON
        context = ""
        if record.results:
            context_parts = []
            results_list = record.results if isinstance(record.results, list) else []
            for r in results_list[:3]:
                meta = r.get("metadata", {})
                doc = r.get("document", "")[:200]
                context_parts.append(f"{meta.get('title', '')} - {meta.get('company', '')}: {doc}")
            context = "\n".join(context_parts)

        scores = evaluate_response(
            intent=record.intent,
            query=record.query,
            response=record.response,
            context=context,
        )

        if scores["relevance"] is None:
            skipped += 1
            continue

        # Save to DB
        eval_record = EvalResult(
            match_history_id=record.id,
            intent=record.intent,
            query=record.query,
            response=record.response,
            context=context[:3000] if context else None,
            relevance=scores["relevance"],
            groundedness=scores["groundedness"],
            helpfulness=scores["helpfulness"],
            avg_score=scores["avg_score"],
            judge_reasoning=scores["reasoning"],
        )
        db.add(eval_record)
        db.commit()

        evaluated += 1
        for key in total_scores:
            total_scores[key] += scores[key]

        logger.info(
            f"Evaluated [{record.intent}] avg={scores['avg_score']:.2f} "
            f"(rel={scores['relevance']:.1f} grnd={scores['groundedness']:.1f} help={scores['helpfulness']:.1f})"
        )

    # Calculate averages
    avg = {}
    if evaluated > 0:
        avg = {k: round(v / evaluated, 3) for k, v in total_scores.items()}

    summary = {
        "evaluated": evaluated,
        "skipped": skipped,
        "averages": avg,
    }
    logger.info(f"Batch eval complete: {summary}")
    return summary


def log_to_mlflow(summary: dict) -> None:
    """Log evaluation summary to MLflow."""
    try:
        import mlflow

        mlflow.set_experiment("job-scanner-eval")
        with mlflow.start_run():
            mlflow.log_metric("evaluated_count", summary["evaluated"])
            mlflow.log_metric("skipped_count", summary["skipped"])
            for key, value in summary.get("averages", {}).items():
                mlflow.log_metric(f"avg_{key}", value)

        logger.info("Logged eval results to MLflow.")
    except ImportError:
        logger.warning("MLflow not installed, skipping.")
    except Exception as e:
        logger.warning(f"MLflow logging failed: {e}")
