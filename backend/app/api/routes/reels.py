"""Reel endpoints: list/filter, detail, stats, update, retry, PDF."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_db, pagination, parse_dt
from app.core.constants import FAILED_STATUSES, PENDING_STATUSES, ProcessingStatus, RETRYABLE_STATUSES
from app.models.pdf_template import PdfTemplate
from app.models.reel import Reel
from app.schemas.common import Page
from app.schemas.reel import (
    CategoryCount,
    ReelDetail,
    ReelListItem,
    ReelStats,
    ReelUpdate,
    RetryResponse,
)
from app.services.search.service import ReelFilters, apply_filters

router = APIRouter(prefix="/reels", tags=["reels"])


@router.get("", response_model=Page[ReelListItem])
def list_reels(
    db: Session = Depends(get_db),
    pg: PaginationParams = Depends(pagination),
    category: str | None = None,
    creator: str | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort: str = Query("shared_at_desc", pattern="^(shared_at_desc|shared_at_asc|created_desc)$"),
):
    f = ReelFilters(
        category=category, creator=creator, status=status,
        date_from=parse_dt(date_from), date_to=parse_dt(date_to),
    )
    stmt = apply_filters(select(Reel), f)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    order = {
        "shared_at_desc": Reel.shared_at.desc().nullslast(),
        "shared_at_asc": Reel.shared_at.asc().nullsfirst(),
        "created_desc": Reel.created_at.desc(),
    }[sort]
    rows = db.scalars(stmt.order_by(order).limit(pg.limit).offset(pg.offset)).all()
    return Page(items=rows, total=int(total), page=pg.page, page_size=pg.page_size)


@router.get("/stats", response_model=ReelStats)
def reel_stats(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(Reel.id))) or 0
    status_rows = db.execute(select(Reel.processing_status, func.count(Reel.id)).group_by(Reel.processing_status)).all()
    by_status = {s: int(c) for s, c in status_rows}
    completed = by_status.get(str(ProcessingStatus.COMPLETED), 0)
    # PENDING_STATUSES already includes DISCOVERED.
    pending = sum(by_status.get(str(s), 0) for s in PENDING_STATUSES)
    failed = sum(by_status.get(str(s), 0) for s in FAILED_STATUSES)
    cat_rows = db.execute(
        select(Reel.category, func.count(Reel.id)).where(Reel.category.is_not(None)).group_by(Reel.category).order_by(func.count(Reel.id).desc())
    ).all()
    by_category = [CategoryCount(category=c, count=int(n)) for c, n in cat_rows]
    return ReelStats(
        total=int(total), completed=completed, pending=pending, failed=failed,
        by_category=by_category, by_status=by_status,
    )


@router.get("/{reel_id}", response_model=ReelDetail)
def get_reel(reel_id: int, db: Session = Depends(get_db)):
    reel = db.get(Reel, reel_id)
    if reel is None:
        raise HTTPException(404, "Reel not found")
    return reel


@router.patch("/{reel_id}", response_model=ReelDetail)
def update_reel(reel_id: int, payload: ReelUpdate, db: Session = Depends(get_db)):
    reel = db.get(Reel, reel_id)
    if reel is None:
        raise HTTPException(404, "Reel not found")
    data = payload.model_dump(exclude_unset=True)
    if "category" in data or "subcategories" in data:
        reel.category_source = "manual"  # protect from being overwritten by re-processing
    for k, v in data.items():
        setattr(reel, k, v)
    db.commit()
    db.refresh(reel)
    return reel


@router.post("/{reel_id}/retry", response_model=RetryResponse)
def retry_reel(reel_id: int, db: Session = Depends(get_db)):
    reel = db.get(Reel, reel_id)
    if reel is None:
        raise HTTPException(404, "Reel not found")
    previous = reel.processing_status
    if previous not in {str(s) for s in RETRYABLE_STATUSES} and previous != str(ProcessingStatus.COMPLETED):
        # Allow retry from failure states or to re-run a completed reel.
        raise HTTPException(409, f"Reel in status '{previous}' is not retryable.")

    from app.workers.dispatch import enqueue_reel

    reel.processing_error = None
    db.commit()
    enqueue_reel(reel_id)
    db.refresh(reel)
    return RetryResponse(
        reel_id=reel_id, previous_status=previous, status=reel.processing_status, queued=True
    )


@router.get("/{reel_id}/pdf")
def export_reel_pdf(reel_id: int, template_id: int | None = None, db: Session = Depends(get_db)):
    reel = db.get(Reel, reel_id)
    if reel is None:
        raise HTTPException(404, "Reel not found")
    config = None
    if template_id is not None:
        tpl = db.get(PdfTemplate, template_id)
        config = tpl.config if tpl else None
    from app.services.pdf.renderer import reel_pdf

    try:
        pdf = reel_pdf(reel, config)
    except Exception as exc:  # WeasyPrint missing or render error
        raise HTTPException(503, f"PDF generation unavailable: {exc}")
    filename = f"reel_{reel.shortcode or reel.id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
