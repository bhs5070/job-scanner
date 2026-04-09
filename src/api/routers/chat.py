"""Chat API router."""

import asyncio
import copy
import logging

from fastapi import APIRouter, Cookie, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.deps import delete_session, get_graph, get_or_create_session
from src.api.routers.auth import _verify_token

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
    latency_ms: int | None = None


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, auth_token: str = Cookie(default="")) -> ChatResponse:
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
        import time as _time
        _start = _time.time()

        # graph.invoke is synchronous — run in thread pool to avoid blocking the event loop
        result = await asyncio.to_thread(graph.invoke, invoke_state)

        _latency_ms = int((_time.time() - _start) * 1000)

        # Persist updated messages for multi-turn
        state["messages"] = result.get("messages", state.get("messages", []))

        intent = result.get("intent")
        response_text = result.get("final_response", "응답을 생성하지 못했습니다.")
        search_results = result.get("search_results")

        # Auto-save to history + conversation (background)
        if intent in ("resume_match", "skill_gap", "job_search"):
            asyncio.create_task(_save_history(
                request, intent, response_text, search_results, auth_token,
            ))
        asyncio.create_task(_save_conversation(
            session_id, request.message, response_text, auth_token,
        ))

        return ChatResponse(
            session_id=session_id,
            intent=intent,
            confidence=result.get("intent_confidence"),
            response=response_text,
            search_results=search_results,
            latency_ms=_latency_ms,
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="에이전트 처리 중 오류가 발생했습니다.")


async def _save_history(
    request: ChatRequest, intent: str, response: str, results: list | None,
    auth_token: str = "",
) -> None:
    """Save match/search results to history DB (fire-and-forget)."""
    try:
        from src.db.models import MatchHistory
        from src.db.session import SessionLocal

        data = _verify_token(auth_token)
        if not data:
            return  # Don't save for unauthenticated users

        db = SessionLocal()
        try:
            record = MatchHistory(
                user_email=data["email"],
                query=request.message,
                intent=intent,
                results=results,
                response=response,
            )
            db.add(record)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to save history: {e}")


async def _save_conversation(
    session_id: str, user_msg: str, ai_msg: str, auth_token: str = "",
) -> None:
    """Save conversation to DB (fire-and-forget)."""
    try:
        from sqlalchemy import select

        from src.db.models import Conversation
        from src.db.session import SessionLocal

        data = _verify_token(auth_token)
        if not data:
            return

        db = SessionLocal()
        try:
            conv = db.scalars(
                select(Conversation).where(Conversation.session_id == session_id)
            ).first()

            title = user_msg[:30] + "..." if len(user_msg) > 30 else user_msg
            msgs = []
            if conv and conv.messages:
                msgs = conv.messages

            msgs.append({"role": "user", "content": user_msg})
            msgs.append({"role": "ai", "content": ai_msg})

            if conv:
                conv.messages = msgs
                conv.title = conv.title if len(msgs) > 2 else title
            else:
                conv = Conversation(
                    user_email=data["email"],
                    session_id=session_id,
                    title=title,
                    messages=msgs,
                )
                db.add(conv)

            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to save conversation: {e}")


@router.delete("/{session_id}")
async def end_session(session_id: str) -> dict:
    """Delete a chat session."""
    delete_session(session_id)
    return {"status": "ok"}
