"""Chat API schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    query: str
    knowledge_base_id: int | None = None
    session_id: int | None = None


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    citations: list | None = None
    created_at: datetime | None = None


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    knowledge_base_id: int | None = None
    title: str | None = None
    created_at: datetime | None = None


class ChatSessionDetail(ChatSessionOut):
    messages: list[ChatMessageOut] = []


class ChatResponse(BaseModel):
    session_id: int
    answer: ChatMessageOut
