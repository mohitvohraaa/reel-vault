"""ReelVault FastAPI application."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    categories,
    chat,
    collections,
    ingestion,
    knowledge_bases,
    pdf,
    reels,
    search,
)
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging()
log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_all is a safety net; Alembic migrations are the source of truth.
    try:
        from app.core.database import init_db

        init_db()
    except Exception:  # pragma: no cover - don't crash API if DB not ready
        log.exception("init_db failed on startup (continuing; run migrations)")
    yield


app = FastAPI(
    title="ReelVault API",
    version="1.0.0",
    description="Turn Instagram DM exports into a searchable, structured knowledge vault.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "llm_provider": settings.llm_provider,
        "embedding_provider": settings.embedding_provider,
    }


_P = settings.api_prefix
app.include_router(ingestion.router, prefix=_P)
app.include_router(reels.router, prefix=_P)
app.include_router(collections.router, prefix=_P)
app.include_router(categories.router, prefix=_P)
app.include_router(knowledge_bases.router, prefix=_P)
app.include_router(chat.router, prefix=_P)
app.include_router(search.router, prefix=_P)
app.include_router(pdf.router, prefix=_P)
app.include_router(pdf.templates_router, prefix=_P)
