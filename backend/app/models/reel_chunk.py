"""Reel text chunks with embeddings — powers semantic search and RAG."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.database import Base
from app.models.types import EmbeddingType


class ReelChunk(Base):
    __tablename__ = "reel_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reel_id: Mapped[int] = mapped_column(
        ForeignKey("reels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="transcript")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list | None] = mapped_column(
        EmbeddingType(settings.embedding_dim), nullable=True
    )

    reel: Mapped["Reel"] = relationship(back_populates="chunks")
