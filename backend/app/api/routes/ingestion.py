"""Ingestion endpoints: upload → conversations → import → jobs."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.models.ingestion_job import IngestionJob
from app.schemas.ingestion import ConversationOut, ImportRequest, JobOut, UploadResponse
from app.services.ingestion import service as ingestion_service
from app.utils.files import ensure_dir, safe_filename

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

_ALLOWED_SUFFIXES = {".zip", ".json"}


@router.post("/upload", response_model=UploadResponse)
async def upload_export(db: Session = Depends(get_db), file: UploadFile = File(...)):
    filename = safe_filename(file.filename or "export")
    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(400, f"Unsupported file type '{suffix}'. Upload a .zip or .json export.")

    ensure_dir(settings.upload_dir)
    dest = Path(settings.upload_dir) / filename

    size = 0
    with dest.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_bytes:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"File exceeds max size of {settings.max_upload_mb} MB.")
            out.write(chunk)

    job = ingestion_service.create_job(db, source_filename=filename, source_path=str(dest))
    job = ingestion_service.parse_conversations(db, job)
    if job.status == "failed":
        raise HTTPException(422, f"Failed to parse export: {job.errors}")

    convos = [ConversationOut(**c) for c in (job.report or {}).get("conversations", [])]
    return UploadResponse(job_id=job.id, status=job.status, conversations=convos)


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(job_id: int, db: Session = Depends(get_db)):
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(404, "Ingestion job not found")
    return [ConversationOut(**c) for c in (job.report or {}).get("conversations", [])]


@router.post("/import", response_model=JobOut)
def start_import(payload: ImportRequest, db: Session = Depends(get_db)):
    job = db.get(IngestionJob, payload.job_id)
    if job is None:
        raise HTTPException(404, "Ingestion job not found")
    job = ingestion_service.import_conversation(db, job, payload.thread_id)
    return job


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    return db.scalars(select(IngestionJob).order_by(IngestionJob.id.desc())).all()


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(404, "Ingestion job not found")
    return job
