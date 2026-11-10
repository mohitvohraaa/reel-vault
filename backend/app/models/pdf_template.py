"""User-customizable PDF export templates."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

JSONVariant = JSON().with_variant(JSONB, "postgresql")


class PdfTemplate(Base):
    __tablename__ = "pdf_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    config: Mapped[dict] = mapped_column(JSONVariant, nullable=False, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
