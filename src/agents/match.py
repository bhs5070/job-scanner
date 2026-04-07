import logging

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.state import AgentState
from src.agents.utils import (
    deduplicate_results,
    format_results_for_llm,
    get_llm,
    render_prompt,
    results_to_state,
)
from src.common.prompts import load_prompt
from src.indexing.retriever import search_jobs

logger = logging.getLogger(__name__)


def match(state: AgentState) -> dict:
    """Match user resume/skills against job postings."""
    llm = get_llm(temperature=0)
    user_input = state["user_input"]

    try:
        # Truncate long resume text for embedding
        query = user_input[:2000]

        raw_results = search_jobs(query=query, n_results=10, where={"is_active": True})
        results = deduplicate_results(raw_results)[:5]

        formatted = format_results_for_llm(results)
        prompt = render_prompt(
            load_prompt("match_analysis"),
            resume_text=user_input,
            search_results=formatted,
            user_input=user_input,
        )

        response = llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=user_input),
        ])

        return {
            "search_results": results_to_state(results),
            "final_response": response.content,
        }

    except Exception as e:
        logger.error(f"Match agent failed: {e}")
        return {
            "final_response": "매칭 분석 중 오류가 발생했습니다. 다시 시도해 주세요.",
            "error": str(e),
        }
