"""Shared utilities for agent nodes."""

from functools import lru_cache

from langchain_openai import ChatOpenAI

from src.common.config import get_settings
from src.indexing.retriever import SearchResult


@lru_cache(maxsize=4)
def get_llm(temperature: float = 0) -> ChatOpenAI:
    """Get a cached LLM client instance."""
    settings = get_settings()
    return ChatOpenAI(
        model=settings.CHAT_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=temperature,
    )


def deduplicate_results(results: list[SearchResult]) -> list[SearchResult]:
    """Keep only the best result per job_id."""
    seen: dict[str, SearchResult] = {}
    for r in results:
        if r.job_id not in seen or r.distance < seen[r.job_id].distance:
            seen[r.job_id] = r
    return list(seen.values())


def format_results_for_llm(results: list[SearchResult]) -> str:
    """Format search results as structured text for LLM context."""
    if not results:
        return "(검색 결과 없음)"

    parts = []
    for i, r in enumerate(results, 1):
        meta = r.metadata
        score = round(1 - r.distance, 2) if r.distance else 0
        doc_preview = r.document[:300] if r.document else ""
        parts.append(
            f"[공고 {i}]\n"
            f"직무: {meta.get('title', 'N/A')}\n"
            f"회사: {meta.get('company', 'N/A')}\n"
            f"출처: {meta.get('source_site', 'N/A')} | URL: {meta.get('source_url', 'N/A')}\n"
            f"유사도: {score}\n"
            f"내용: {doc_preview}\n"
        )
    return "\n".join(parts)


def results_to_state(results: list[SearchResult]) -> list[dict]:
    """Convert SearchResults to serializable dicts for state."""
    return [
        {"job_id": r.job_id, "metadata": r.metadata, "document": r.document, "distance": r.distance}
        for r in results
    ]


def render_prompt(template: str, **kwargs: str) -> str:
    """Safely render a prompt template with keyword arguments.

    Uses a single-pass replacement to avoid cross-contamination
    where one variable's value contains another variable's placeholder.
    """
    for key, value in kwargs.items():
        placeholder = "{" + key + "}"
        template = template.replace(placeholder, value)
    return template
