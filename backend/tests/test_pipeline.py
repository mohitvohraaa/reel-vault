"""Pipeline tests: happy path, insufficient content, failure isolation, retry.

Media download and transcription are disabled in the test env, so the pipeline
summarizes from the caption via the stub provider and embeds via the stub
embedder — fully offline.
"""
from __future__ import annotations

import pytest

from app.core.constants import ProcessingStatus
from app.models.reel import Reel
from app.models.reel_chunk import ReelChunk
from app.services import pipeline as pipeline_mod
from app.workers.dispatch import run_reel_inline


def _make_reel(db, *, url, caption=None):
    reel = Reel(
        reel_url=url, normalized_url=url, shortcode=url.rstrip("/").split("/")[-1],
        caption=caption, processing_status=ProcessingStatus.DISCOVERED,
    )
    db.add(reel)
    db.commit()
    db.refresh(reel)
    return reel


def test_reel_with_caption_completes_and_is_embedded(db):
    reel = _make_reel(
        db,
        url="https://www.instagram.com/reel/CapOne111/",
        caption="A practical guide to building AI agents in Python with tools.",
    )
    status = run_reel_inline(reel.id)
    assert status == str(ProcessingStatus.COMPLETED)

    db.refresh(reel)
    assert reel.title
    assert reel.summary
    assert reel.category
    chunks = db.query(ReelChunk).filter(ReelChunk.reel_id == reel.id).all()
    assert len(chunks) >= 1
    assert chunks[0].embedding is not None


def test_reel_without_content_is_insufficient(db):
    reel = _make_reel(db, url="https://www.instagram.com/reel/NoText222/", caption=None)
    status = run_reel_inline(reel.id)
    assert status == str(ProcessingStatus.INSUFFICIENT_CONTENT)
    db.refresh(reel)
    assert reel.processing_status == str(ProcessingStatus.INSUFFICIENT_CONTENT)


def test_one_failing_reel_does_not_affect_another(db, monkeypatch):
    good = _make_reel(db, url="https://www.instagram.com/reel/Good333/", caption="startup growth tips for founders")
    bad = _make_reel(db, url="https://www.instagram.com/reel/Bad444/", caption="some content here indeed today")

    original = pipeline_mod.summarize_reel

    def flaky(**kwargs):
        if "some content here" in (kwargs.get("caption") or ""):
            raise RuntimeError("boom")
        return original(**kwargs)

    monkeypatch.setattr(pipeline_mod, "summarize_reel", flaky)

    assert run_reel_inline(good.id) == str(ProcessingStatus.COMPLETED)
    assert run_reel_inline(bad.id) == str(ProcessingStatus.SUMMARIZATION_FAILED)

    db.refresh(bad)
    assert bad.processing_error is not None  # failure recorded, not lost


def test_retry_resumes_failed_reel(db):
    reel = _make_reel(db, url="https://www.instagram.com/reel/Retry555/", caption="finance budgeting basics for beginners")
    reel.processing_status = ProcessingStatus.SUMMARIZATION_FAILED
    reel.processing_error = "previous failure"
    db.commit()

    status = run_reel_inline(reel.id)  # resumes from summarization
    assert status == str(ProcessingStatus.COMPLETED)
    db.refresh(reel)
    assert reel.processing_error is None


def test_processing_logs_written(db):
    reel = _make_reel(db, url="https://www.instagram.com/reel/Logs666/", caption="productivity workflow tips")
    run_reel_inline(reel.id)
    from app.models.processing_log import ProcessingLog

    logs = db.query(ProcessingLog).filter(ProcessingLog.reel_id == reel.id).all()
    stages = {l.stage for l in logs}
    assert "summarization" in stages
    assert "embedding" in stages
