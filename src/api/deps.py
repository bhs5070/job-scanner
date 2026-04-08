"""FastAPI dependencies."""

import uuid
from collections.abc import Generator
from functools import lru_cache

from fastapi import Cookie, HTTPException
from sqlalchemy.orm import Session

from src.agents import AgentState, compile_graph
from src.api.routers.auth import _verify_token
from src.db.session import SessionLocal

# In-memory session store (single process, MVP)
_sessions: dict[str, AgentState] = {}


@lru_cache(maxsize=1)
def get_graph() -> "CompiledStateGraph":
    """Get the compiled agent graph (singleton)."""
    from langgraph.graph.state import CompiledStateGraph  # noqa: F811
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


def get_current_user_email(auth_token: str = Cookie(default="")) -> str:
    """Dependency: get authenticated user's email or raise 401."""
    data = _verify_token(auth_token)
    if not data:
        raise HTTPException(status_code=401, detail="Login required")
    return data["email"]


def get_db() -> Generator[Session, None, None]:
    """Dependency: get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
