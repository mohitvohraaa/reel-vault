"""Per-stage processing logs with timing and error context."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProcessingLog(Base):
    __tablename__ = "processing_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reel_id: Mapped[int] = mapped_column(
        ForeignKey("reels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reel: Mapped["Reel"] = relationship(back_populates="logs")
