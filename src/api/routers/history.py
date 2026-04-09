"""Match history API router."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.deps import get_current_user_email, get_db
from src.db.models import MatchHistory

router = APIRouter(prefix="/api/history", tags=["history"])

HISTORY_RESPONSE_PREVIEW_LENGTH = 300  # Characters to return per history item


class HistoryResponse(BaseModel):
    id: str
    query: str
    intent: str
    response: str
    created_at: str


@router.get("")
async def list_history(
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> list[HistoryResponse]:
    stmt = (
        select(MatchHistory)
        .where(MatchHistory.user_email == email)
        .order_by(MatchHistory.created_at.desc())
        .limit(30)
    )
    rows = db.scalars(stmt).all()
    return [
        HistoryResponse(
            id=str(r.id), query=r.query, intent=r.intent,
            response=r.response[:HISTORY_RESPONSE_PREVIEW_LENGTH], created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]
