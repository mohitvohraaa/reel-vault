"""Collection endpoints — manual grouping / categorization of reels."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.collection import Collection
from app.models.reel import Reel
from app.schemas.collection import CollectionCreate, CollectionOut, ReelIds
from app.schemas.common import Message
from app.utils.text import slugify

router = APIRouter(prefix="/collections", tags=["collections"])


def _to_out(c: Collection) -> CollectionOut:
    return CollectionOut(
        id=c.id, name=c.name, slug=c.slug, color=c.color,
        description=c.description, created_at=c.created_at, reel_count=len(c.reels),
    )


@router.post("", response_model=CollectionOut, status_code=201)
def create_collection(payload: CollectionCreate, db: Session = Depends(get_db)):
    slug = slugify(payload.name)
    if db.scalar(select(Collection).where(Collection.slug == slug)):
        raise HTTPException(409, "A collection with this name already exists.")
    c = Collection(name=payload.name, slug=slug, color=payload.color, description=payload.description)
    db.add(c)
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.get("", response_model=list[CollectionOut])
def list_collections(db: Session = Depends(get_db)):
    return [_to_out(c) for c in db.scalars(select(Collection).order_by(Collection.name)).all()]


@router.get("/{collection_id}", response_model=CollectionOut)
def get_collection(collection_id: int, db: Session = Depends(get_db)):
    c = db.get(Collection, collection_id)
    if c is None:
        raise HTTPException(404, "Collection not found")
    return _to_out(c)


@router.delete("/{collection_id}", response_model=Message)
def delete_collection(collection_id: int, db: Session = Depends(get_db)):
    c = db.get(Collection, collection_id)
    if c is None:
        raise HTTPException(404, "Collection not found")
    db.delete(c)
    db.commit()
    return Message(message="deleted")


@router.post("/{collection_id}/reels", response_model=CollectionOut)
def add_reels(collection_id: int, payload: ReelIds, db: Session = Depends(get_db)):
    c = db.get(Collection, collection_id)
    if c is None:
        raise HTTPException(404, "Collection not found")
    reels = db.scalars(select(Reel).where(Reel.id.in_(payload.reel_ids))).all()
    existing = {r.id for r in c.reels}
    for r in reels:
        if r.id not in existing:
            c.reels.append(r)
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.delete("/{collection_id}/reels", response_model=CollectionOut)
def remove_reels(collection_id: int, payload: ReelIds, db: Session = Depends(get_db)):
    c = db.get(Collection, collection_id)
    if c is None:
        raise HTTPException(404, "Collection not found")
    remove = set(payload.reel_ids)
    c.reels = [r for r in c.reels if r.id not in remove]
    db.commit()
    db.refresh(c)
    return _to_out(c)
