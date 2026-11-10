"""Cross-dialect column types.

``EmbeddingType`` uses real pgvector on PostgreSQL and degrades to JSON on
other dialects (e.g. SQLite in tests) so ``create_all`` works everywhere.
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.types import TypeDecorator

try:  # pgvector is only needed at runtime on Postgres
    from pgvector.sqlalchemy import Vector

    _HAS_PGVECTOR = True
except Exception:  # pragma: no cover
    Vector = None  # type: ignore
    _HAS_PGVECTOR = False


class EmbeddingType(TypeDecorator):
    """Vector(dim) on PostgreSQL, JSON list elsewhere."""

    impl = sa.JSON
    cache_ok = True

    def __init__(self, dim: int, *args, **kwargs):
        self.dim = dim
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and _HAS_PGVECTOR:
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(sa.JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        value = list(value)
        if dialect.name == "postgresql" and _HAS_PGVECTOR:
            return value
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return list(value)
