"""Chat API router."""

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.deps import delete_session, get_graph, get_or_create_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    intent: str | None
    confidence: float | None
    response: str
    search_results: list[dict] | None = None


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to the agent and get a response."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session_id, state = get_or_create_session(request.session_id)
    graph = get_graph()

    # Update state with new user input
    state["user_input"] = request.message
    state["intent"] = None
    state["intent_confidence"] = None
    state["search_results"] = None
    state["final_response"] = None
    state["error"] = None

    try:
        # graph.invoke is synchronous — run in thread pool to avoid blocking the event loop
        result = await asyncio.to_thread(graph.invoke, state)

        # Persist updated messages for multi-turn
        state["messages"] = result.get("messages", state.get("messages", []))

        return ChatResponse(
            session_id=session_id,
            intent=result.get("intent"),
            confidence=result.get("intent_confidence"),
            response=result.get("final_response", "응답을 생성하지 못했습니다."),
            search_results=result.get("search_results"),
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="에이전트 처리 중 오류가 발생했습니다.")


@router.delete("/{session_id}")
async def end_session(session_id: str) -> dict:
    """Delete a chat session."""
    delete_session(session_id)
    return {"status": "ok"}
