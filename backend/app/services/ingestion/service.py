"""Ingestion orchestration: upload → parse → conversation selection → import."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import JobStatus, ProcessingStatus
from app.core.logging import get_logger
from app.models.ingestion_job import IngestionJob
from app.models.reel import Reel
from app.services.ingestion.report import conversations_report, import_report
from app.services.instagram.parser import ExportParser
from app.utils.files import ensure_dir

log = get_logger("ingestion")


def _workdir_for(job_id: int) -> Path:
    return ensure_dir(Path(settings.upload_dir) / f"job_{job_id}")


def create_job(db: Session, *, source_filename: str, source_path: str) -> IngestionJob:
    job = IngestionJob(
        source_filename=source_filename,
        source_path=source_path,
        status=JobStatus.PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def parse_conversations(db: Session, job: IngestionJob) -> IngestionJob:
    """Parse the uploaded export and record the list of conversations."""
    job.status = JobStatus.PARSING
    db.commit()
    try:
        parser = ExportParser.from_source(job.source_path, _workdir_for(job.id))
        summaries = parser.list_conversations()
        report = conversations_report(summaries)
        job.total_conversations = report["total_conversations"]
        job.total_messages = report["total_messages"]
        job.reels_found = report["total_reels_detected"]
        job.report = report
        job.status = JobStatus.PARSED
        db.commit()
    except Exception as exc:  # pragma: no cover - defensive
        log.exception("parse failed for job %s", job.id)
        job.status = JobStatus.FAILED
        job.errors = [str(exc)]
        db.commit()
    db.refresh(job)
    return job


def import_conversation(db: Session, job: IngestionJob, thread_id: str) -> IngestionJob:
    """Parse the selected conversation, create de-duplicated Reel rows and
    enqueue processing. Idempotent: re-running will not create duplicates."""
    job.status = JobStatus.IMPORTING
    job.conversation_thread_id = thread_id
    db.commit()

    parser = ExportParser.from_source(job.source_path, _workdir_for(job.id))
    result = parser.parse_conversation(thread_id)
    job.conversation_name = result.title

    new_reel_ids: list[int] = []
    existing_skipped = 0

    for parsed in result.reels:
        existing = db.scalar(
            select(Reel).where(Reel.normalized_url == parsed.normalized_url)
        )
        if existing is not None:
            existing_skipped += 1
            continue
        reel = Reel(
            reel_url=parsed.reel_url,
            normalized_url=parsed.normalized_url,
            shortcode=parsed.shortcode,
            creator_username=parsed.creator_username,
            caption=parsed.caption,
            shared_at=parsed.shared_at,
            original_message_id=parsed.original_message_id,
            ingestion_job_id=job.id,
            processing_status=ProcessingStatus.DISCOVERED,
        )
        db.add(reel)
        try:
            db.commit()
        except Exception:
            # Unique-constraint race: another import created it; skip.
            db.rollback()
            existing_skipped += 1
            continue
        db.refresh(reel)
        new_reel_ids.append(reel.id)

    job.reels_unique = len(result.reels)
    job.duplicates_skipped = result.duplicates_skipped
    job.unsupported = result.unsupported
    job.parse_errors = len(result.parse_errors)
    job.total_messages = result.messages_scanned
    job.reels_found = result.reel_urls_found
    # Merge import stats into the report without discarding the conversations list
    # (so GET /conversations still works after an import).
    job.report = {
        **(job.report or {}),
        **import_report(result, new_reels=len(new_reel_ids), existing_skipped=existing_skipped),
    }
    job.status = JobStatus.PROCESSING
    db.commit()

    # Enqueue processing (Celery or inline) — one task per reel.
    from app.workers.dispatch import enqueue_reel  # lazy import avoids cycles

    for reel_id in new_reel_ids:
        enqueue_reel(reel_id)

    if not new_reel_ids:
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

    db.refresh(job)
    return job
