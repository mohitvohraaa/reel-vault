"""initial schema

Creates the pgvector extension, all tables (from model metadata), and the
special PostgreSQL indexes: a functional GIN index for full-text search and an
ivfflat index for vector similarity.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-10
"""
from __future__ import annotations

from alembic import op

from app.core.config import settings
from app.core.database import Base
import app.models  # noqa: F401  (register all tables on Base.metadata)

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # pgvector must exist before tables with vector columns are created.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create all tables from the current model metadata.
    Base.metadata.create_all(bind=bind)

    # Full-text search: functional GIN index over the searchable text columns.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_reels_fts ON reels
        USING GIN (
            to_tsvector(
                'english',
                coalesce(title,'') || ' ' || coalesce(summary,'') || ' ' ||
                coalesce(transcript,'') || ' ' || coalesce(caption,'')
            )
        )
        """
    )

    # Vector similarity index (ivfflat, cosine). Safe to attempt; ignored if the
    # table is empty/needs ANALYZE — it still speeds up larger datasets.
    try:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_reel_chunks_embedding ON reel_chunks "
            f"USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
        )
    except Exception:
        pass


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_reel_chunks_embedding")
    op.execute("DROP INDEX IF EXISTS ix_reels_fts")
    Base.metadata.drop_all(bind=op.get_bind())
