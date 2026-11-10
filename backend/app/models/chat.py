"""Chat sessions and messages for RAG over knowledge bases."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

JSONVariant = JSON().with_variant(JSONB, "postgresql")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    knowledge_base_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ChatMessage.id",
        lazy="selectin",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
