"""Match history API router."""

from fastapi import APIRouter, Cookie, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.routers.auth import _verify_token
from src.db.models import MatchHistory
from src.db.session import SessionLocal

router = APIRouter(prefix="/api/history", tags=["history"])


def _get_user_email(auth_token: str = Cookie(default="")) -> str:
    data = _verify_token(auth_token)
    if not data:
        raise HTTPException(status_code=401, detail="Login required")
    return data["email"]


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class HistoryResponse(BaseModel):
    id: str
    query: str
    intent: str
    response: str
    created_at: str


@router.get("")
async def list_history(
    email: str = Depends(_get_user_email),
    db: Session = Depends(_get_db),
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
