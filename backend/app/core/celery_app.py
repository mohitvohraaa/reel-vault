"""Celery application for background processing."""
from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "reelvault",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="reelvault",
    result_expires=3600,
)
