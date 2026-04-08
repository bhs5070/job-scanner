"""FastAPI dependencies."""

import uuid
from functools import lru_cache

from src.agents import AgentState, compile_graph

# In-memory session store (single process, MVP)
_sessions: dict[str, AgentState] = {}


@lru_cache(maxsize=1)
def get_graph():
    """Get the compiled agent graph (singleton)."""
    return compile_graph()


def delete_session(session_id: str) -> None:
    """Delete a session from the in-memory store."""
    _sessions.pop(session_id, None)


def get_or_create_session(session_id: str | None = None) -> tuple[str, AgentState]:
    """Get existing session or create a new one."""
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]

    new_id = session_id or str(uuid.uuid4())
    state: AgentState = {
        "messages": [],
        "user_input": "",
        "intent": None,
        "intent_confidence": None,
        "search_results": None,
        "final_response": None,
        "error": None,
    }
    _sessions[new_id] = state
    return new_id, state
