"""Ingestion API schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConversationOut(BaseModel):
    thread_id: str
    title: str | None = None
    participants: list[str] = []
    message_count: int = 0
    reel_count: int = 0


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_filename: str | None = None
    conversation_name: str | None = None
    conversation_thread_id: str | None = None
    status: str
    total_conversations: int = 0
    total_messages: int = 0
    reels_found: int = 0
    reels_unique: int = 0
    duplicates_skipped: int = 0
    unsupported: int = 0
    parse_errors: int = 0
    reels_processed: int = 0
    errors: list | None = None
    report: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class UploadResponse(BaseModel):
    job_id: int
    status: str
    conversations: list[ConversationOut]


class ImportRequest(BaseModel):
    job_id: int
    thread_id: str
