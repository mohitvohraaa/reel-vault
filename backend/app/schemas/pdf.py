"""PDF export + template API schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PdfTemplateCreate(BaseModel):
    name: str
    config: dict = {}
    is_default: bool = False


class PdfTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    config: dict
    is_default: bool
    created_at: datetime | None = None


class ExportRequest(BaseModel):
    # Exactly one scope should be provided.
    reel_ids: list[int] | None = None
    collection_id: int | None = None
    knowledge_base_id: int | None = None
    filter: dict | None = None
    template_id: int | None = None
    title: str | None = None
