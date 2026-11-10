"""Knowledge base API schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.reel import ReelListItem


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str | None = None
    source_type: str = "manual"  # conversation | collection | manual | filter
    # Depending on source_type:
    thread_id: str | None = None          # conversation
    collection_id: int | None = None      # collection
    reel_ids: list[int] | None = None     # manual
    filter: dict | None = None            # filter (category/creator/status/date)


class KnowledgeBaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    source_type: str
    source_ref: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    reel_count: int = 0


class KnowledgeBaseDetail(KnowledgeBaseOut):
    reels: list[ReelListItem] = []
