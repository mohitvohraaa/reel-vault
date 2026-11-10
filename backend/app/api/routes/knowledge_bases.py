"""Knowledge base endpoints — named, scoped sets of reels for RAG chat."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, parse_dt
from app.core.constants import KBSourceType
from app.models.collection import Collection
from app.models.ingestion_job import IngestionJob
from app.models.knowledge_base import KnowledgeBase
from app.models.reel import Reel
from app.schemas.common import Message
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseDetail, KnowledgeBaseOut
from app.schemas.collection import ReelIds
from app.services.search.service import ReelFilters, apply_filters

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


def _resolve_members(db: Session, payload: KnowledgeBaseCreate) -> tuple[list[Reel], dict]:
    st = payload.source_type
    if st == KBSourceType.CONVERSATION:
        if not payload.thread_id:
            raise HTTPException(400, "thread_id is required for a conversation knowledge base")
        job_ids = [
            j.id for j in db.scalars(
                select(IngestionJob).where(IngestionJob.conversation_thread_id == payload.thread_id)
            ).all()
        ]
        reels = db.scalars(select(Reel).where(Reel.ingestion_job_id.in_(job_ids))).all() if job_ids else []
        return list(reels), {"thread_id": payload.thread_id}
    if st == KBSourceType.COLLECTION:
        c = db.get(Collection, payload.collection_id) if payload.collection_id else None
        if c is None:
            raise HTTPException(404, "Collection not found")
        return list(c.reels), {"collection_id": c.id}
    if st == KBSourceType.MANUAL:
        ids = payload.reel_ids or []
        reels = db.scalars(select(Reel).where(Reel.id.in_(ids))).all() if ids else []
        return list(reels), {"reel_ids": ids}
    if st == KBSourceType.FILTER:
        fl = payload.filter or {}
        f = ReelFilters(
            category=fl.get("category"), creator=fl.get("creator"), status=fl.get("status"),
            date_from=parse_dt(fl.get("date_from")), date_to=parse_dt(fl.get("date_to")),
        )
        reels = db.scalars(apply_filters(select(Reel), f)).all()
        return list(reels), {"filter": fl}
    raise HTTPException(400, f"Unknown source_type '{st}'")


def _to_out(kb: KnowledgeBase) -> KnowledgeBaseOut:
    return KnowledgeBaseOut(
        id=kb.id, name=kb.name, description=kb.description, source_type=kb.source_type,
        source_ref=kb.source_ref, created_at=kb.created_at, updated_at=kb.updated_at,
        reel_count=len(kb.reels),
    )


def _to_detail(kb: KnowledgeBase) -> KnowledgeBaseDetail:
    from app.schemas.reel import ReelListItem

    return KnowledgeBaseDetail(
        **_to_out(kb).model_dump(),
        reels=[ReelListItem.model_validate(r) for r in kb.reels],
    )


@router.post("", response_model=KnowledgeBaseDetail, status_code=201)
def create_kb(payload: KnowledgeBaseCreate, db: Session = Depends(get_db)):
    members, source_ref = _resolve_members(db, payload)
    kb = KnowledgeBase(
        name=payload.name, description=payload.description,
        source_type=payload.source_type, source_ref=source_ref,
    )
    kb.reels = members
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return _to_detail(kb)


@router.get("", response_model=list[KnowledgeBaseOut])
def list_kbs(db: Session = Depends(get_db)):
    return [_to_out(kb) for kb in db.scalars(select(KnowledgeBase).order_by(KnowledgeBase.id.desc())).all()]


@router.get("/{kb_id}", response_model=KnowledgeBaseDetail)
def get_kb(kb_id: int, db: Session = Depends(get_db)):
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(404, "Knowledge base not found")
    return _to_detail(kb)


@router.post("/{kb_id}/reels", response_model=KnowledgeBaseDetail)
def add_kb_reels(kb_id: int, payload: ReelIds, db: Session = Depends(get_db)):
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(404, "Knowledge base not found")
    reels = db.scalars(select(Reel).where(Reel.id.in_(payload.reel_ids))).all()
    existing = {r.id for r in kb.reels}
    for r in reels:
        if r.id not in existing:
            kb.reels.append(r)
    db.commit()
    db.refresh(kb)
    return _to_detail(kb)


@router.delete("/{kb_id}", response_model=Message)
def delete_kb(kb_id: int, db: Session = Depends(get_db)):
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(404, "Knowledge base not found")
    db.delete(kb)
    db.commit()
    return Message(message="deleted")
