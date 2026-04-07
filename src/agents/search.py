import json
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


def _rewrite_query(user_input: str) -> tuple[str, str]:
    """Rewrite user input into an optimized search query."""
    llm = get_llm(temperature=0)
    system_prompt = load_prompt("search_query_rewrite")
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input),
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        result = json.loads(raw)
        return result.get("query", user_input), result.get("chunk_type", "full")
    except Exception as e:
        logger.warning(f"Query rewrite failed, using raw input: {e}")
        return user_input, "full"


def search(state: AgentState) -> dict:
    """Search for job postings using vector similarity."""
    llm = get_llm(temperature=0)

    try:
        query, chunk_type = _rewrite_query(state["user_input"])
        logger.info(f"Search query: {query}, chunk_type: {chunk_type}")

        where_filter: dict = {"is_active": True}
        if chunk_type != "full":
            where_filter["chunk_type"] = chunk_type

        raw_results = search_jobs(query, n_results=10, where=where_filter)
        results = deduplicate_results(raw_results)[:5]

        formatted = format_results_for_llm(results)
        response_prompt = render_prompt(
            load_prompt("search_response"),
            search_results=formatted,
            user_input=state["user_input"],
        )

        response = llm.invoke([
            SystemMessage(content=response_prompt),
            HumanMessage(content=state["user_input"]),
        ])

        return {
            "search_results": results_to_state(results),
            "final_response": response.content,
        }

    except Exception as e:
        logger.error(f"Search agent failed: {e}")
        return {
            "final_response": "검색 중 오류가 발생했습니다. 다시 시도해 주세요.",
            "error": str(e),
        }
