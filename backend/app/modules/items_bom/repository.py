"""All database queries for items and BOM live here."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.items_bom.models import BomComponent, Item


def list_items(db: Session, *, search: str | None = None) -> list[Item]:
    """List items, optionally filtered by code or name."""
    stmt = select(Item).order_by(Item.code)
    if search:
        needle = f"%{search.lower()}%"
        stmt = stmt.where(Item.name.ilike(needle) | Item.code.ilike(needle))
    return list(db.execute(stmt).scalars().all())


def get_item(db: Session, code: str) -> Item | None:
    """Fetch a single item by code."""
    return db.get(Item, code)


def components_of(db: Session, parent_code: str) -> list[BomComponent]:
    """Return the direct components of a parent item, ordered by stage."""
    stmt = (
        select(BomComponent)
        .where(BomComponent.parent_code == parent_code)
        .order_by(BomComponent.stage)
    )
    return list(db.execute(stmt).scalars().all())


def add_item(db: Session, item: Item) -> Item:
    """Persist an item."""
    db.add(item)
    db.flush()
    return item


def add_components(db: Session, components: list[BomComponent]) -> None:
    """Bulk-insert BOM edges."""
    db.add_all(components)
    db.flush()
