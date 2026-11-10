"""Pydantic schema for validated LLM structured output."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.constants import CONTENT_TYPES, IMPORTANCE_LEVELS


class ReelSummary(BaseModel):
    """Structured understanding of a reel. All list fields default to empty so a
    partial/omitted LLM response still validates rather than discarding the reel."""

    title: str = Field(default="Untitled Reel", max_length=300)
    one_liner: str = ""
    summary: str = ""
    category: str = "Interesting / Miscellaneous"
    subcategories: list[str] = Field(default_factory=list)
    key_takeaways: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    actionable_insights: list[str] = Field(default_factory=list)
    content_type: str = "other"
    importance: str = "medium"
    language: str = "en"
    has_sufficient_content: bool = True

    @field_validator("title", "one_liner", "summary", "category", "content_type", "importance", "language", mode="before")
    @classmethod
    def _coerce_str(cls, v):
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("subcategories", "key_takeaways", "entities", "actionable_insights", mode="before")
    @classmethod
    def _coerce_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return []

    @field_validator("content_type")
    @classmethod
    def _valid_content_type(cls, v):
        return v if v in CONTENT_TYPES else "other"

    @field_validator("importance")
    @classmethod
    def _valid_importance(cls, v):
        return v if v in IMPORTANCE_LEVELS else "medium"

    @field_validator("title")
    @classmethod
    def _nonempty_title(cls, v):
        return v or "Untitled Reel"
