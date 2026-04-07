from typing import TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    """Central state schema for the LangGraph agent system."""

    # Conversation history
    messages: list[BaseMessage]

    # Current turn
    user_input: str

    # Router output
    intent: str | None
    intent_confidence: float | None

    # Retrieval results (shared across Search/Match/Gap)
    search_results: list[dict] | None

    # Final response text (consumed by respond node)
    final_response: str | None

    # Error propagation
    error: str | None
