"""User collections — manual grouping / categorization of reels."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

reel_collections = Table(
    "reel_collections",
    Base.metadata,
    Column("reel_id", ForeignKey("reels.id", ondelete="CASCADE"), primary_key=True),
    Column("collection_id", ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True),
)


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reels: Mapped[list["Reel"]] = relationship(secondary=reel_collections, lazy="selectin")
