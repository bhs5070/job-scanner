"""Conversation history API router."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.deps import get_current_user_email, get_db
from src.db.models import Conversation

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationItem(BaseModel):
    id: str
    session_id: str
    title: str
    updated_at: str


@router.get("")
async def list_conversations(
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> list[ConversationItem]:
    stmt = (
        select(Conversation)
        .where(Conversation.user_email == email)
        .order_by(Conversation.updated_at.desc())
        .limit(20)
    )
    rows = db.scalars(stmt).all()
    return [
        ConversationItem(
            id=str(c.id), session_id=c.session_id,
            title=c.title, updated_at=c.updated_at.isoformat(),
        )
        for c in rows
    ]


@router.get("/{session_id}")
async def get_conversation(
    session_id: str,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> dict:
    conv = db.scalars(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_email == email,
        )
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": str(conv.id),
        "session_id": conv.session_id,
        "title": conv.title,
        "messages": conv.messages or [],
    }
