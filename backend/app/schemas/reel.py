"""Reel API schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReelBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reel_url: str
    normalized_url: str
    shortcode: str | None = None
    creator_username: str | None = None
    caption: str | None = None
    thumbnail_url: str | None = None
    shared_at: datetime | None = None
    title: str | None = None
    one_liner: str | None = None
    category: str | None = None
    subcategories: list[str] | None = None
    content_type: str | None = None
    importance: str | None = None
    language: str | None = None
    processing_status: str
    created_at: datetime | None = None


class ReelListItem(ReelBase):
    """Lightweight item for list/search responses (no heavy transcript)."""


class ReelDetail(ReelBase):
    summary: str | None = None
    key_takeaways: list[str] | None = None
    entities: list[str] | None = None
    actionable_insights: list[str] | None = None
    transcript: str | None = None
    transcript_language: str | None = None
    transcript_segments: list | None = None
    duration_sec: float | None = None
    processing_error: str | None = None
    category_source: str | None = None
    original_message_id: str | None = None
    ingestion_job_id: int | None = None
    updated_at: datetime | None = None


class ReelUpdate(BaseModel):
    """Manual edits — e.g. re-categorization. Sets category_source='manual'."""
    title: str | None = None
    category: str | None = None
    subcategories: list[str] | None = None
    importance: str | None = None
    content_type: str | None = None


class CategoryCount(BaseModel):
    category: str
    count: int


class ReelStats(BaseModel):
    total: int
    completed: int
    pending: int
    failed: int
    by_category: list[CategoryCount]
    by_status: dict[str, int]


class RetryResponse(BaseModel):
    reel_id: int
    previous_status: str
    status: str
    queued: bool
