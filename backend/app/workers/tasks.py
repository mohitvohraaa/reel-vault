"""Celery tasks for asynchronous reel processing."""
from __future__ import annotations

from app.core.celery_app import celery_app
from app.core.logging import get_logger

log = get_logger("tasks")


@celery_app.task(name="reelvault.process_reel", bind=True, max_retries=2, default_retry_delay=30)
def process_reel_task(self, reel_id: int) -> str:
    """Process one reel. Pipeline stages handle their own failures and persist
    per-stage status, so a failed reel is recorded, not lost."""
    from app.workers.dispatch import run_reel_inline

    try:
        return run_reel_inline(reel_id)
    except Exception as exc:  # pragma: no cover - defensive; infra-level errors only
        log.exception("task failed for reel %s", reel_id)
        raise self.retry(exc=exc)
