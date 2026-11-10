"""Search service: keyword (FTS), semantic (pgvector), and hybrid.

Modular by design so Phase 3 can extend/replace retrieval without touching the
API layer. Works on PostgreSQL (real tsvector + pgvector) and degrades to
portable SQL + in-Python cosine on SQLite for tests.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Float, func, or_, select
from sqlalchemy.orm import Session

from app.models.reel import Reel
from app.models.reel_chunk import ReelChunk
from app.services.embeddings.embedder import embed_query


@dataclass
class ReelFilters:
    category: str | None = None
    creator: str | None = None
    status: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


def apply_filters(stmt, f: ReelFilters):
    if f.category:
        stmt = stmt.where(Reel.category == f.category)
    if f.creator:
        stmt = stmt.where(Reel.creator_username == f.creator)
    if f.status:
        stmt = stmt.where(Reel.processing_status == f.status)
    if f.date_from:
        stmt = stmt.where(Reel.shared_at >= f.date_from)
    if f.date_to:
        stmt = stmt.where(Reel.shared_at <= f.date_to)
    return stmt


def _is_postgres(db: Session) -> bool:
    return db.bind.dialect.name == "postgresql"


# ----------------------------------------------------------------------- keyword
def keyword_search(db: Session, query: str, f: ReelFilters, limit: int, offset: int) -> tuple[list[Reel], int]:
    base = apply_filters(select(Reel), f)
    q = (query or "").strip()
    if q:
        if _is_postgres(db):
            doc = func.to_tsvector(
                "english",
                func.coalesce(Reel.title, "")
                + " "
                + func.coalesce(Reel.summary, "")
                + " "
                + func.coalesce(Reel.transcript, "")
                + " "
                + func.coalesce(Reel.caption, ""),
            )
            base = base.where(doc.op("@@")(func.plainto_tsquery("english", q)))
        else:
            like = f"%{q.lower()}%"
            base = base.where(
                or_(
                    func.lower(func.coalesce(Reel.title, "")).like(like),
                    func.lower(func.coalesce(Reel.summary, "")).like(like),
                    func.lower(func.coalesce(Reel.transcript, "")).like(like),
                    func.lower(func.coalesce(Reel.caption, "")).like(like),
                )
            )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(base.order_by(Reel.shared_at.desc().nullslast()).limit(limit).offset(offset)).all()
    return list(rows), int(total)


# ---------------------------------------------------------------------- semantic
def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def semantic_reel_ids(db: Session, qvec: list[float], f: ReelFilters, limit: int,
                      restrict_ids: list[int] | None = None) -> list[tuple[int, float]]:
    """Return [(reel_id, similarity)] ranked by best-matching chunk."""
    if _is_postgres(db):
        from pgvector.sqlalchemy import Vector
        from sqlalchemy import bindparam

        from app.core.config import settings as _settings

        # Use the pgvector cosine-distance operator (<=>) with a typed bind param.
        # (ReelChunk.embedding is wrapped in a TypeDecorator, which does not proxy
        # Vector's custom comparator methods, so we build the operator explicitly.)
        qparam = bindparam("qvec", value=qvec, type_=Vector(_settings.embedding_dim))
        # return_type=Float: the <=> operator yields a scalar distance, not a vector.
        # Without it the result inherits the Vector type and pgvector tries to parse
        # the float distance as a vector literal.
        dist = ReelChunk.embedding.op("<=>", return_type=Float)(qparam)
        best_col = func.min(dist).label("best")
        stmt = select(ReelChunk.reel_id, best_col).join(Reel, Reel.id == ReelChunk.reel_id)
        stmt = apply_filters(stmt, f)
        if restrict_ids is not None:
            if not restrict_ids:
                return []
            stmt = stmt.where(ReelChunk.reel_id.in_(restrict_ids))
        stmt = stmt.group_by(ReelChunk.reel_id).order_by(best_col).limit(limit)
        rows = db.execute(stmt).all()
        return [(rid, 1.0 - float(best)) for rid, best in rows]

    # SQLite / fallback: compute cosine in Python.
    stmt = select(ReelChunk.reel_id, ReelChunk.embedding).join(Reel, Reel.id == ReelChunk.reel_id)
    stmt = apply_filters(stmt, f)
    if restrict_ids is not None:
        if not restrict_ids:
            return []
        stmt = stmt.where(ReelChunk.reel_id.in_(restrict_ids))
    best: dict[int, float] = {}
    for reel_id, emb in db.execute(stmt).all():
        if not emb:
            continue
        sim = _cosine(qvec, list(emb))
        if reel_id not in best or sim > best[reel_id]:
            best[reel_id] = sim
    ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return ranked


def semantic_search(db: Session, query: str, f: ReelFilters, limit: int, offset: int) -> tuple[list[Reel], int]:
    qvec = embed_query(query)
    ranked = semantic_reel_ids(db, qvec, f, limit + offset)
    page = ranked[offset: offset + limit]
    ids = [rid for rid, _ in page]
    reels = {r.id: r for r in db.scalars(select(Reel).where(Reel.id.in_(ids))).all()} if ids else {}
    ordered = [reels[rid] for rid, _ in page if rid in reels]
    return ordered, len(ranked)


# ------------------------------------------------------------------------ hybrid
def hybrid_search(db: Session, query: str, f: ReelFilters, limit: int, offset: int) -> tuple[list[Reel], int]:
    kw, _ = keyword_search(db, query, f, limit=limit + offset, offset=0)
    qvec = embed_query(query)
    sem = semantic_reel_ids(db, qvec, f, limit=limit + offset)

    scores: dict[int, float] = {}
    for rank, reel in enumerate(kw):
        scores[reel.id] = scores.get(reel.id, 0.0) + 1.0 / (rank + 1)
    for rank, (rid, _sim) in enumerate(sem):
        scores[rid] = scores.get(rid, 0.0) + 1.0 / (rank + 1)

    ranked_ids = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)
    page_ids = ranked_ids[offset: offset + limit]
    reels = {r.id: r for r in db.scalars(select(Reel).where(Reel.id.in_(page_ids))).all()} if page_ids else {}
    ordered = [reels[i] for i in page_ids if i in reels]
    return ordered, len(ranked_ids)


def search(db: Session, *, query: str, mode: str, f: ReelFilters, limit: int, offset: int) -> tuple[list[Reel], int]:
    if mode == "semantic":
        return semantic_search(db, query, f, limit, offset)
    if mode == "hybrid":
        return hybrid_search(db, query, f, limit, offset)
    return keyword_search(db, query, f, limit, offset)
