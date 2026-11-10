"""Hierarchical category taxonomy endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.constants import DEFAULT_CATEGORIES
from app.models.category import Category
from app.schemas.collection import CategoryCreate, CategoryOut
from app.schemas.common import Message

router = APIRouter(prefix="/categories", tags=["categories"])


def _build_tree(cats: list[Category]) -> list[CategoryOut]:
    by_parent: dict[int | None, list[Category]] = {}
    for c in cats:
        by_parent.setdefault(c.parent_id, []).append(c)

    def build(parent_id: int | None) -> list[CategoryOut]:
        return [
            CategoryOut(id=c.id, name=c.name, parent_id=c.parent_id, children=build(c.id))
            for c in sorted(by_parent.get(parent_id, []), key=lambda x: x.name)
        ]

    return build(None)


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    cats = db.scalars(select(Category)).all()
    return _build_tree(list(cats))


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    if payload.parent_id is not None and db.get(Category, payload.parent_id) is None:
        raise HTTPException(404, "Parent category not found")
    c = Category(name=payload.name, parent_id=payload.parent_id)
    db.add(c)
    db.commit()
    db.refresh(c)
    return CategoryOut(id=c.id, name=c.name, parent_id=c.parent_id, children=[])


@router.delete("/{category_id}", response_model=Message)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    c = db.get(Category, category_id)
    if c is None:
        raise HTTPException(404, "Category not found")
    db.delete(c)
    db.commit()
    return Message(message="deleted")


@router.post("/seed-defaults", response_model=list[CategoryOut])
def seed_defaults(db: Session = Depends(get_db)):
    """Populate the taxonomy with the default top-level categories (idempotent)."""
    existing = {c.name for c in db.scalars(select(Category)).all()}
    for name in DEFAULT_CATEGORIES:
        if name not in existing:
            db.add(Category(name=name))
    db.commit()
    return _build_tree(list(db.scalars(select(Category)).all()))
