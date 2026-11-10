"""Reel processing pipeline orchestration.

Runs stages in order, writes a processing_logs row per stage, updates the reel's
single ``processing_status``, and is idempotent + retryable. One reel failing
never raises out of here in a way that would stop a batch — the caller catches,
and each reel's state is persisted independently.

Stage order: metadata -> media -> transcription -> summarization -> embedding
A non-fatal media failure (private/sound-withheld reel) does NOT stop the
pipeline: if a caption exists the reel is still summarized and completed; only
when there is neither usable transcript nor caption is it marked
``insufficient_content``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.constants import ProcessingStatus, Stage
from app.core.logging import get_logger
from app.models.processing_log import ProcessingLog
from app.models.reel import Reel
from app.models.reel_chunk import ReelChunk
from app.services.embeddings.embedder import embed_reel
from app.services.media.retriever import MediaRetriever
from app.services.summarization.llm import summarize_reel
from app.services.transcription.transcriber import Transcriber
from app.utils.text import word_count

log = get_logger("pipeline")

STAGE_ORDER = [Stage.METADATA, Stage.MEDIA, Stage.TRANSCRIPTION, Stage.SUMMARIZATION, Stage.EMBEDDING]

# Where to resume when retrying a failed reel.
_RESUME_STAGE = {
    ProcessingStatus.DISCOVERED: Stage.METADATA,
    ProcessingStatus.METADATA_EXTRACTED: Stage.MEDIA,
    ProcessingStatus.MEDIA_UNAVAILABLE: Stage.MEDIA,
    ProcessingStatus.TRANSCRIPTION_FAILED: Stage.TRANSCRIPTION,
    ProcessingStatus.INSUFFICIENT_CONTENT: Stage.MEDIA,
    ProcessingStatus.SUMMARIZATION_FAILED: Stage.SUMMARIZATION,
    ProcessingStatus.EMBEDDING_FAILED: Stage.EMBEDDING,
    ProcessingStatus.COMPLETED: Stage.METADATA,
}


@dataclass
class _Ctx:
    media_ok: bool = False
    media_failure: str | None = None
    notes: list[str] = field(default_factory=list)


def _log_stage(db: Session, reel_id: int, stage: Stage, status: str, error: str | None, elapsed: float) -> None:
    db.add(
        ProcessingLog(
            reel_id=reel_id,
            stage=str(stage),
            status=status,
            error_message=error,
            execution_time=round(elapsed, 3),
        )
    )
    db.commit()


def _set_status(db: Session, reel: Reel, status: ProcessingStatus, error: str | None = None) -> None:
    reel.processing_status = str(status)
    reel.processing_error = error
    db.commit()


def _media_present(reel: Reel) -> bool:
    import os

    return bool(reel.media_path and os.path.exists(reel.media_path))


# ----------------------------------------------------------------------- stages
def _stage_metadata(db: Session, reel: Reel, ctx: _Ctx) -> tuple[bool, ProcessingStatus | None]:
    # Metadata was captured at ingest; this stage validates/marks it. Never fabricate.
    _set_status(db, reel, ProcessingStatus.METADATA_EXTRACTED)
    return True, None


def _stage_media(db: Session, reel: Reel, ctx: _Ctx) -> tuple[bool, ProcessingStatus | None]:
    _set_status(db, reel, ProcessingStatus.DOWNLOADING)
    if _media_present(reel):
        ctx.media_ok = True
        return True, None
    result = MediaRetriever().retrieve_audio(reel.normalized_url, reel.shortcode)
    if result.ok:
        reel.media_path = result.media_path
        reel.duration_sec = result.duration_sec
        db.commit()
        ctx.media_ok = True
        return True, None
    # Non-fatal: retain the reel and continue; summarization may use the caption.
    ctx.media_ok = False
    ctx.media_failure = f"{result.reason}: {result.error}"
    ctx.notes.append(f"media unavailable ({result.reason})")
    return True, None


def _stage_transcription(db: Session, reel: Reel, ctx: _Ctx) -> tuple[bool, ProcessingStatus | None]:
    if not ctx.media_ok:
        return True, None  # nothing to transcribe; summarization will use caption
    if reel.transcript:
        return True, None  # idempotent: already transcribed
    _set_status(db, reel, ProcessingStatus.TRANSCRIBING)
    result = Transcriber().transcribe(reel.media_path)  # type: ignore[arg-type]
    if not result.ok:
        return False, ProcessingStatus.TRANSCRIPTION_FAILED
    reel.transcript = result.text or None
    reel.transcript_language = result.language
    reel.transcript_segments = result.segments or None
    db.commit()
    return True, None


def _has_usable_content(reel: Reel, min_words: int) -> bool:
    from app.core.config import settings

    if word_count(reel.transcript) >= min_words:
        return True
    if word_count(reel.caption) >= min_words:
        return True
    # A short transcript plus any caption is still something.
    return bool((reel.transcript or "").strip() or (reel.caption or "").strip())


def _stage_summarization(db: Session, reel: Reel, ctx: _Ctx) -> tuple[bool, ProcessingStatus | None]:
    from app.core.config import settings

    if not _has_usable_content(reel, settings.min_speech_words):
        note = "; ".join(ctx.notes) or "no transcript or caption available"
        return False, ProcessingStatus.INSUFFICIENT_CONTENT
    _set_status(db, reel, ProcessingStatus.SUMMARIZING)
    metadata = {
        "creator_username": reel.creator_username,
        "shared_at": reel.shared_at.isoformat() if reel.shared_at else None,
        "reel_url": reel.normalized_url,
        "media_note": ctx.media_failure,
    }
    try:
        summary = summarize_reel(
            transcript=reel.transcript,
            caption=reel.caption,
            metadata=metadata,
            language=reel.transcript_language,
        )
    except Exception as exc:
        return False, ProcessingStatus.SUMMARIZATION_FAILED

    reel.title = summary.title
    reel.one_liner = summary.one_liner
    reel.summary = summary.summary
    if reel.category_source != "manual":  # never clobber a manual re-categorization
        reel.category = summary.category
        reel.subcategories = summary.subcategories
    reel.key_takeaways = summary.key_takeaways
    reel.entities = summary.entities
    reel.actionable_insights = summary.actionable_insights
    reel.content_type = summary.content_type
    reel.importance = summary.importance
    reel.language = summary.language
    db.commit()

    if not summary.has_sufficient_content:
        return False, ProcessingStatus.INSUFFICIENT_CONTENT
    return True, None


def _stage_embedding(db: Session, reel: Reel, ctx: _Ctx) -> tuple[bool, ProcessingStatus | None]:
    _set_status(db, reel, ProcessingStatus.EMBEDDING)
    try:
        chunks = embed_reel(transcript=reel.transcript, summary=reel.summary, caption=reel.caption)
        # Idempotent: replace any existing chunks.
        db.execute(delete(ReelChunk).where(ReelChunk.reel_id == reel.id))
        for ch in chunks:
            db.add(
                ReelChunk(
                    reel_id=reel.id,
                    chunk_index=ch.index,
                    source=ch.source,
                    content=ch.content,
                    embedding=ch.embedding,
                )
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        return False, ProcessingStatus.EMBEDDING_FAILED
    return True, None


_STAGE_FUNCS = {
    Stage.METADATA: _stage_metadata,
    Stage.MEDIA: _stage_media,
    Stage.TRANSCRIPTION: _stage_transcription,
    Stage.SUMMARIZATION: _stage_summarization,
    Stage.EMBEDDING: _stage_embedding,
}


def process_reel(db: Session, reel_id: int, *, from_status: str | None = None) -> str:
    """Process a single reel through the pipeline. Returns the final status.

    Resumes from the stage implied by the reel's current status (or ``from_status``),
    which makes both initial processing and retries idempotent."""
    reel = db.get(Reel, reel_id)
    if reel is None:
        return "missing"

    status = from_status or reel.processing_status
    start_stage = _RESUME_STAGE.get(ProcessingStatus(status) if status in ProcessingStatus._value2member_map_ else ProcessingStatus.DISCOVERED, Stage.METADATA)
    start_idx = STAGE_ORDER.index(start_stage)
    reel.processing_error = None
    db.commit()

    ctx = _Ctx()
    # If resuming past media, reflect whether media already exists.
    ctx.media_ok = _media_present(reel)

    for stage in STAGE_ORDER[start_idx:]:
        func = _STAGE_FUNCS[stage]
        started = time.perf_counter()
        try:
            ok, fail_status = func(db, reel, ctx)
        except Exception as exc:  # unexpected stage crash — isolate it
            log.exception("stage %s crashed for reel %s", stage, reel_id)
            elapsed = time.perf_counter() - started
            _log_stage(db, reel_id, stage, "error", str(exc), elapsed)
            _set_status(db, reel, _default_fail_status(stage), error=str(exc))
            return reel.processing_status
        elapsed = time.perf_counter() - started
        if ok:
            _log_stage(db, reel_id, stage, "ok", ("; ".join(ctx.notes) or None) if stage == Stage.MEDIA else None, elapsed)
        else:
            err = ctx.media_failure if stage == Stage.MEDIA else (reel.processing_error or str(fail_status))
            _log_stage(db, reel_id, stage, "failed", err, elapsed)
            _set_status(db, reel, fail_status, error=err or f"{stage} failed")
            return reel.processing_status

    _set_status(db, reel, ProcessingStatus.COMPLETED, error=ctx.media_failure)
    return reel.processing_status


def _default_fail_status(stage: Stage) -> ProcessingStatus:
    return {
        Stage.MEDIA: ProcessingStatus.MEDIA_UNAVAILABLE,
        Stage.TRANSCRIPTION: ProcessingStatus.TRANSCRIPTION_FAILED,
        Stage.SUMMARIZATION: ProcessingStatus.SUMMARIZATION_FAILED,
        Stage.EMBEDDING: ProcessingStatus.EMBEDDING_FAILED,
    }.get(stage, ProcessingStatus.SUMMARIZATION_FAILED)
