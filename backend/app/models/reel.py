"""Reel ORM model — the central entity."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ProcessingStatus
from app.core.database import Base

# Use JSONB on Postgres; SQLAlchemy JSON on SQLite via variant.
from sqlalchemy import JSON

JSONVariant = JSON().with_variant(JSONB, "postgresql")


class Reel(Base):
    __tablename__ = "reels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # --- Identity / source metadata (never fabricated) ---
    reel_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    normalized_url: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    shortcode: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    creator_username: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    shared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    original_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ingestion_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # --- Media / transcription ---
    media_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    transcript_segments: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)

    # --- LLM-derived understanding ---
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    one_liner: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    subcategories: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    key_takeaways: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    entities: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    actionable_insights: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    importance: Mapped[str | None] = mapped_column(String(32), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    category_source: Mapped[str] = mapped_column(String(16), default="ai", nullable=False)

    # --- Processing state ---
    processing_status: Mapped[str] = mapped_column(
        String(32), default=ProcessingStatus.DISCOVERED, nullable=False, index=True
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Relationships ---
    chunks: Mapped[list["ReelChunk"]] = relationship(
        back_populates="reel", cascade="all, delete-orphan", passive_deletes=True
    )
    logs: Mapped[list["ProcessingLog"]] = relationship(
        back_populates="reel", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index("ix_reels_status_shared", "processing_status", "shared_at"),
    )


from app.models.reel_chunk import ReelChunk  # noqa: E402
from app.models.processing_log import ProcessingLog  # noqa: E402
