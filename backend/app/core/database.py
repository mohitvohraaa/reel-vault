"""Database engine, session factory and declarative base."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


_connect_args: dict = {}
if settings.database_url.startswith("sqlite"):
    # Allow cross-thread use (FastAPI TestClient runs the app in a worker thread).
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create the pgvector extension and all tables.

    Used as a safety net on startup and in tests. In production the
    Alembic migration is the source of truth, but ``create_all`` is
    idempotent and will not drop/alter existing tables.
    """
    from sqlalchemy import text

    import app.models  # noqa: F401  (ensure models are imported/registered)

    with engine.begin() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            # pgvector may be unavailable (e.g. sqlite in tests); ignore.
            pass
    Base.metadata.create_all(bind=engine)
