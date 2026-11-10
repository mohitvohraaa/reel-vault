"""Knowledge bases — named, scoped sets of reels used for RAG chat."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import KBSourceType
from app.core.database import Base

JSONVariant = JSON().with_variant(JSONB, "postgresql")

knowledge_base_reels = Table(
    "knowledge_base_reels",
    Base.metadata,
    Column("knowledge_base_id", ForeignKey("knowledge_bases.id", ondelete="CASCADE"), primary_key=True),
    Column("reel_id", ForeignKey("reels.id", ondelete="CASCADE"), primary_key=True),
)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), default=KBSourceType.MANUAL, nullable=False)
    source_ref: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    reels: Mapped[list["Reel"]] = relationship(secondary=knowledge_base_reels, lazy="selectin")
