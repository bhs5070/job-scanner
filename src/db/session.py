from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.common.config import get_settings


@lru_cache(maxsize=1)
def _get_engine() -> Engine:
    return create_engine(get_settings().DATABASE_URL, echo=False)


@lru_cache(maxsize=1)
def _get_session_factory() -> sessionmaker:
    return sessionmaker(bind=_get_engine(), autocommit=False, autoflush=False)


def SessionLocal() -> Session:  # type: ignore[override]
    """Create a new DB session. Lazily initializes engine on first call."""
    return _get_session_factory()()
