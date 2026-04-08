"""Chat API router."""

import asyncio
import copy
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.api.deps import delete_session, get_graph, get_or_create_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=36)
    profile_context: str | None = Field(default=None, max_length=8000)


class ChatResponse(BaseModel):
    session_id: str
    intent: str | None
    confidence: float | None
    response: str
    search_results: list[dict] | None = None


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to the agent and get a response."""
    session_id, state = get_or_create_session(request.session_id)
    graph = get_graph()

    # Create a copy to avoid race conditions on concurrent requests
    invoke_state = copy.copy(state)
    # Prepend profile context to user input if provided
    user_input = request.message
    if request.profile_context:
        user_input = f"[사용자 프로필 정보]\n{request.profile_context}\n\n[질문]\n{request.message}"
    invoke_state["user_input"] = user_input
    invoke_state["intent"] = None
    invoke_state["intent_confidence"] = None
    invoke_state["search_results"] = None
    invoke_state["final_response"] = None
    invoke_state["error"] = None

    try:
        # graph.invoke is synchronous — run in thread pool to avoid blocking the event loop
        result = await asyncio.to_thread(graph.invoke, invoke_state)

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
