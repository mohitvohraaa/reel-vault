"""Dispatch reel processing to Celery or run it inline (tests / no broker)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import JobStatus, PENDING_STATUSES
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.models.ingestion_job import IngestionJob
from app.models.reel import Reel
from app.services.pipeline import process_reel

log = get_logger("worker")


def _update_job_progress(db: Session, reel: Reel) -> None:
    if reel.ingestion_job_id is None:
        return
    job = db.get(IngestionJob, reel.ingestion_job_id)
    if job is None:
        return
    # Count reels for this job that are no longer pending/in-flight.
    reels = db.scalars(select(Reel).where(Reel.ingestion_job_id == job.id)).all()
    done = sum(1 for r in reels if r.processing_status not in {str(s) for s in PENDING_STATUSES})
    job.reels_processed = done
    if reels and done >= len(reels):
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
    db.commit()


def run_reel_inline(reel_id: int) -> str:
    db = SessionLocal()
    try:
        status = process_reel(db, reel_id)
        reel = db.get(Reel, reel_id)
        if reel is not None:
            _update_job_progress(db, reel)
        return status
    except Exception:  # one reel must never take down the batch
        log.exception("inline processing failed for reel %s", reel_id)
        return "error"
    finally:
        db.close()


def enqueue_reel(reel_id: int) -> None:
    if settings.use_celery:
        from app.workers.tasks import process_reel_task

        process_reel_task.delay(reel_id)
    else:
        run_reel_inline(reel_id)
