"""Test configuration: offline SQLite DB, stub providers, no Celery.

Environment variables are set BEFORE importing any app module so the cached
Settings singleton picks up the test configuration.
"""
from __future__ import annotations

import os
import tempfile

_TMP_DB = os.path.join(tempfile.gettempdir(), "reelvault_test.db")
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)

os.environ.setdefault("DATABASE_URL", f"sqlite+pysqlite:///{_TMP_DB}")
os.environ.setdefault("UPLOAD_DIR", os.path.join(tempfile.gettempdir(), "reelvault_uploads"))
os.environ.setdefault("MEDIA_DIR", os.path.join(tempfile.gettempdir(), "reelvault_media"))
os.environ.setdefault("USE_CELERY", "false")
os.environ.setdefault("MEDIA_DOWNLOAD_ENABLED", "false")
os.environ.setdefault("TRANSCRIPTION_ENABLED", "false")
os.environ.setdefault("LLM_PROVIDER", "stub")
os.environ.setdefault("EMBEDDING_PROVIDER", "stub")
os.environ.setdefault("EMBEDDING_DIM", "64")  # small dim keeps stub vectors light

import json  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_tables(db):
    """Wipe mutable tables between tests for isolation."""
    yield
    from app.models.reel import Reel
    from app.models.ingestion_job import IngestionJob
    from app.models.chat import ChatSession
    from app.models.knowledge_base import KnowledgeBase
    from app.models.collection import Collection

    for model in (ChatSession, KnowledgeBase, Collection, Reel, IngestionJob):
        for row in db.query(model).all():
            db.delete(row)
    db.commit()


# ---------------------------------------------------------- synthetic export
@pytest.fixture()
def sample_export(tmp_path):
    from tests.sample_builder import write_sample_export

    return write_sample_export(tmp_path)
