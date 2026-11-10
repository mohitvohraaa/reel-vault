"""Unified search endpoint: keyword / semantic / hybrid."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_db, pagination, parse_dt
from app.schemas.common import Page
from app.schemas.reel import ReelListItem
from app.services.search.service import ReelFilters, search

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=Page[ReelListItem])
def search_reels(
    db: Session = Depends(get_db),
    pg: PaginationParams = Depends(pagination),
    q: str = Query("", description="Search query"),
    mode: str = Query("keyword", pattern="^(keyword|semantic|hybrid)$"),
    category: str | None = None,
    creator: str | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    f = ReelFilters(
        category=category, creator=creator, status=status,
        date_from=parse_dt(date_from), date_to=parse_dt(date_to),
    )
    rows, total = search(db, query=q, mode=mode, f=f, limit=pg.limit, offset=pg.offset)
    return Page(items=rows, total=int(total), page=pg.page, page_size=pg.page_size)
