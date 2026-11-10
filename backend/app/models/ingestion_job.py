"""Ingestion job tracking (upload → parse → import)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import JobStatus
from app.core.database import Base

JSONVariant = JSON().with_variant(JSONB, "postgresql")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    conversation_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    conversation_thread_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.PENDING, nullable=False)

    total_conversations: Mapped[int] = mapped_column(Integer, default=0)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    reels_found: Mapped[int] = mapped_column(Integer, default=0)
    reels_unique: Mapped[int] = mapped_column(Integer, default=0)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, default=0)
    unsupported: Mapped[int] = mapped_column(Integer, default=0)
    parse_errors: Mapped[int] = mapped_column(Integer, default=0)
    reels_processed: Mapped[int] = mapped_column(Integer, default=0)

    errors: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    report: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
