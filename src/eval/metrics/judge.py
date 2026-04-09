"""LLM-as-Judge evaluation metrics using GPT-4o."""

import json
import logging
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.common.config import get_settings
from src.common.prompts import load_prompt

logger = logging.getLogger(__name__)

LLM_JUDGE_METRICS = [
    "relevance", "groundedness", "helpfulness",
    "faithfulness", "answer_completeness",
    "retrieval_precision", "retrieval_mrr", "context_relevance",
]

JUDGE_MODEL = "gpt-4o"
EVAL_QUERY_MAX_LENGTH = 1000
EVAL_CONTEXT_MAX_LENGTH = 2000
EVAL_RESPONSE_MAX_LENGTH = 2000


@lru_cache(maxsize=1)
def _get_judge() -> ChatOpenAI:
    """Get a cached GPT-4o judge instance."""
    settings = get_settings()
    return ChatOpenAI(model=JUDGE_MODEL, api_key=settings.OPENAI_API_KEY, temperature=0)


def evaluate_response(
    intent: str,
    query: str,
    response: str,
    context: str | None = None,
) -> dict:
    """Evaluate a single agent response using GPT-4o as judge.

    Returns dict with 8 LLM-judged scores (0-1), avg_score, and reasoning.
    """
    judge = _get_judge()

    prompt_template = load_prompt("eval_judge")
    prompt = (
        prompt_template
        .replace("{intent}", intent)
        .replace("{query}", query[:EVAL_QUERY_MAX_LENGTH])
        .replace("{context}", (context or "(없음)")[:EVAL_CONTEXT_MAX_LENGTH])
        .replace("{response}", response[:EVAL_RESPONSE_MAX_LENGTH])
    )

    try:
        result = judge.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content="Evaluate the response above."),
        ])

        raw = result.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        scores = json.loads(raw)

        # Extract all metrics
        output = {}
        total = 0
        count = 0
        for metric in LLM_JUDGE_METRICS:
            val = scores.get(metric)
            if val is not None:
                val = max(0.0, min(1.0, float(val)))
                output[metric] = val
                total += val
                count += 1
            else:
                output[metric] = None

        output["avg_score"] = round(total / count, 3) if count > 0 else None
        output["reasoning"] = scores.get("reasoning", "")
        return output

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return {metric: None for metric in LLM_JUDGE_METRICS} | {
            "avg_score": None,
            "reasoning": f"Evaluation error: {e}",
        }


def evaluate_routing(predicted_intent: str, query: str) -> float:
    """Evaluate routing accuracy by re-classifying the query.

    Returns 1.0 if the re-classification matches, 0.0 otherwise.
    """
    judge = _get_judge()

    prompt = (
        "Classify this query into exactly one category: "
        "job_search, resume_match, skill_gap, trend, chitchat.\n\n"
        f"Query: {query}\n\n"
        "Return ONLY the category name, nothing else."
    )

    try:
        result = judge.invoke([HumanMessage(content=prompt)])
        expected = result.content.strip().lower()
        return 1.0 if expected == predicted_intent else 0.0
    except Exception as e:
        logger.warning(f"Routing eval failed: {e}")
        return 0.0
