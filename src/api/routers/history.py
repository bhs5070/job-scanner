"""Match history API router."""

from src.api.deps import get_current_user_email, get_db
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import MatchHistory

router = APIRouter(prefix="/api/history", tags=["history"])




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
            response=r.response[:300], created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]
