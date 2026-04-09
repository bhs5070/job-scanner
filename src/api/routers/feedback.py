"""User feedback API router."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.deps import get_current_user_email, get_db

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    session_id: str
    feedback: Literal["positive", "negative"]
    reason: str | None = None


@router.post("")
async def submit_feedback(
    req: FeedbackRequest,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> dict:
    """Save user feedback for an agent response."""
    db.execute(text("""
        INSERT INTO user_feedback (id, user_email, session_id, feedback, reason)
        VALUES (:id, :email, :session_id, :feedback, :reason)
    """), {
        "id": str(uuid.uuid4()),
        "email": email,
        "session_id": req.session_id,
        "feedback": req.feedback,
        "reason": req.reason,
    })
    db.commit()
    return {"status": "ok"}
