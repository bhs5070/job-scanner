"""Batch evaluation pipeline: evaluate unevaluated match_history records."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import EvalResult, MatchHistory
from src.eval.metrics.judge import LLM_JUDGE_METRICS, evaluate_response, evaluate_routing

EVAL_BATCH_LIMIT = 50  # Default max records per eval run
CONTEXT_MAX_LENGTH = 3000  # Max context string length stored in DB
CONTEXT_DOC_PREVIEW = 300  # Characters per result document in context

logger = logging.getLogger(__name__)


def run_batch_eval(db: Session, limit: int = EVAL_BATCH_LIMIT) -> dict:
    """Evaluate match_history records that haven't been evaluated yet.

    Scores 10 metrics per record:
    - 8 LLM Judge: relevance, groundedness, helpfulness, faithfulness,
      answer_completeness, retrieval_precision, retrieval_mrr, context_relevance
    - 1 Routing accuracy (GPT-4o re-classification)
    - 1 Latency (from match_history if available)
    """
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
        return {"evaluated": 0, "skipped": 0, "averages": {}}

    logger.info(f"Evaluating {len(records)} records with 10 metrics...")

    evaluated = 0
    skipped = 0
    totals = {m: 0.0 for m in LLM_JUDGE_METRICS}
    totals["routing_accuracy"] = 0.0

    for record in records:
        # Build context from results JSON
        context = _build_context(record.results)

        # 8 LLM Judge metrics
        scores = evaluate_response(
            intent=record.intent,
            query=record.query,
            response=record.response,
            context=context,
        )

        if scores.get("relevance") is None:
            skipped += 1
            continue

        # Routing accuracy
        routing_score = evaluate_routing(record.intent, record.query)

        # Save to DB
        eval_record = EvalResult(
            match_history_id=record.id,
            intent=record.intent,
            query=record.query,
            response=record.response,
            context=context[:CONTEXT_MAX_LENGTH] if context else None,
            relevance=scores["relevance"],
            groundedness=scores["groundedness"],
            helpfulness=scores["helpfulness"],
            faithfulness=scores["faithfulness"],
            answer_completeness=scores["answer_completeness"],
            retrieval_precision=scores["retrieval_precision"],
            retrieval_mrr=scores["retrieval_mrr"],
            context_relevance=scores["context_relevance"],
            routing_accuracy=routing_score,
            avg_score=scores["avg_score"],
            judge_reasoning=scores["reasoning"],
        )
        db.add(eval_record)
        db.commit()

        evaluated += 1
        for m in LLM_JUDGE_METRICS:
            if scores.get(m) is not None:
                totals[m] += scores[m]
        totals["routing_accuracy"] += routing_score

        logger.info(
            f"[{record.intent}] avg={scores['avg_score']:.2f} routing={routing_score:.0f}"
        )

    # Averages
    avg = {}
    if evaluated > 0:
        avg = {k: round(v / evaluated, 3) for k, v in totals.items()}

    summary = {"evaluated": evaluated, "skipped": skipped, "averages": avg}
    logger.info(f"Batch eval complete: {summary}")
    return summary


def _build_context(results: list | None) -> str:
    """Build context string from match_history results JSON."""
    if not results:
        return ""
    results_list = results if isinstance(results, list) else []
    parts = []
    for r in results_list[:5]:
        meta = r.get("metadata", {})
        doc = r.get("document", "")[:CONTEXT_DOC_PREVIEW]
        parts.append(f"{meta.get('title', '')} - {meta.get('company', '')}: {doc}")
    return "\n".join(parts)


MLFLOW_EXPERIMENT_NAME = "job-scanner-eval"


def log_to_mlflow(summary: dict) -> None:
    """Log evaluation summary to MLflow."""
    try:
        import mlflow

        mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
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
