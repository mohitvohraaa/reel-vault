"""Collection and category API schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CollectionCreate(BaseModel):
    name: str
    color: str | None = None
    description: str | None = None


class CollectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    color: str | None = None
    description: str | None = None
    created_at: datetime | None = None
    reel_count: int = 0


class ReelIds(BaseModel):
    reel_ids: list[int]


class CategoryCreate(BaseModel):
    name: str
    parent_id: int | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_id: int | None = None
    children: list["CategoryOut"] = []


CategoryOut.model_rebuild()
