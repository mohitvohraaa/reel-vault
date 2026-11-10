"""PDF export + template management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, parse_dt
from app.models.collection import Collection
from app.models.knowledge_base import KnowledgeBase
from app.models.pdf_template import PdfTemplate
from app.models.reel import Reel
from app.schemas.common import Message
from app.schemas.pdf import ExportRequest, PdfTemplateCreate, PdfTemplateOut
from app.services.search.service import ReelFilters, apply_filters

router = APIRouter(tags=["pdf"])


def _resolve_scope(db: Session, req: ExportRequest) -> tuple[str, list[Reel]]:
    if req.reel_ids:
        reels = db.scalars(select(Reel).where(Reel.id.in_(req.reel_ids))).all()
        return req.title or "Selected Reels", list(reels)
    if req.collection_id is not None:
        c = db.get(Collection, req.collection_id)
        if c is None:
            raise HTTPException(404, "Collection not found")
        return req.title or c.name, list(c.reels)
    if req.knowledge_base_id is not None:
        kb = db.get(KnowledgeBase, req.knowledge_base_id)
        if kb is None:
            raise HTTPException(404, "Knowledge base not found")
        return req.title or kb.name, list(kb.reels)
    if req.filter is not None:
        fl = req.filter
        f = ReelFilters(
            category=fl.get("category"), creator=fl.get("creator"), status=fl.get("status"),
            date_from=parse_dt(fl.get("date_from")), date_to=parse_dt(fl.get("date_to")),
        )
        reels = db.scalars(apply_filters(select(Reel), f).order_by(Reel.shared_at.desc().nullslast())).all()
        return req.title or "Filtered Reels", list(reels)
    raise HTTPException(400, "Provide one of reel_ids, collection_id, knowledge_base_id, or filter.")


@router.post("/export/pdf")
def export_pdf(req: ExportRequest, db: Session = Depends(get_db)):
    title, reels = _resolve_scope(db, req)
    if not reels:
        raise HTTPException(404, "No reels matched the export scope.")
    config = None
    if req.template_id is not None:
        tpl = db.get(PdfTemplate, req.template_id)
        config = tpl.config if tpl else None
    from app.services.pdf.renderer import collection_pdf

    try:
        pdf = collection_pdf(title, reels, config)
    except Exception as exc:
        raise HTTPException(503, f"PDF generation unavailable: {exc}")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="reelvault_export.pdf"'},
    )


# ------------------------------------------------------------------- templates
templates_router = APIRouter(prefix="/pdf-templates", tags=["pdf"])


@templates_router.get("", response_model=list[PdfTemplateOut])
def list_templates(db: Session = Depends(get_db)):
    return db.scalars(select(PdfTemplate).order_by(PdfTemplate.id)).all()


@templates_router.post("", response_model=PdfTemplateOut, status_code=201)
def create_template(payload: PdfTemplateCreate, db: Session = Depends(get_db)):
    if db.scalar(select(PdfTemplate).where(PdfTemplate.name == payload.name)):
        raise HTTPException(409, "A template with this name already exists.")
    tpl = PdfTemplate(name=payload.name, config=payload.config, is_default=payload.is_default)
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@templates_router.patch("/{template_id}", response_model=PdfTemplateOut)
def update_template(template_id: int, payload: PdfTemplateCreate, db: Session = Depends(get_db)):
    tpl = db.get(PdfTemplate, template_id)
    if tpl is None:
        raise HTTPException(404, "Template not found")
    tpl.name = payload.name
    tpl.config = payload.config
    tpl.is_default = payload.is_default
    db.commit()
    db.refresh(tpl)
    return tpl


@templates_router.delete("/{template_id}", response_model=Message)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    tpl = db.get(PdfTemplate, template_id)
    if tpl is None:
        raise HTTPException(404, "Template not found")
    db.delete(tpl)
    db.commit()
    return Message(message="deleted")
