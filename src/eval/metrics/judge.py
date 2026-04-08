"""LLM-as-Judge evaluation metrics using GPT-4o."""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.common.config import get_settings
from src.common.prompts import load_prompt

logger = logging.getLogger(__name__)


def evaluate_response(
    intent: str,
    query: str,
    response: str,
    context: str | None = None,
) -> dict:
    """Evaluate a single agent response using GPT-4o as judge.

    Returns dict with relevance, groundedness, helpfulness scores (0-1)
    and reasoning text.
    """
    settings = get_settings()
    judge = ChatOpenAI(
        model="gpt-4o",  # Stronger model for evaluation
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )

    prompt_template = load_prompt("eval_judge")
    prompt = (
        prompt_template
        .replace("{intent}", intent)
        .replace("{query}", query[:1000])
        .replace("{context}", (context or "(없음)")[:2000])
        .replace("{response}", response[:2000])
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

        relevance = float(scores.get("relevance", 0))
        groundedness = float(scores.get("groundedness", 0))
        helpfulness = float(scores.get("helpfulness", 0))
        avg_score = round((relevance + groundedness + helpfulness) / 3, 3)

        return {
            "relevance": relevance,
            "groundedness": groundedness,
            "helpfulness": helpfulness,
            "avg_score": avg_score,
            "reasoning": scores.get("reasoning", ""),
        }

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return {
            "relevance": None,
            "groundedness": None,
            "helpfulness": None,
            "avg_score": None,
            "reasoning": f"Evaluation error: {e}",
        }
