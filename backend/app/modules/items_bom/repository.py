"""All database queries for items and BOM live here."""

from __future__ import annotations

from sqlalchemy import func, select
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


def history_count(db: Session, code: str) -> int:
    """How many records anywhere refer to this item.

    An item that has been bought, sold, made or consumed carries its code on
    posted transactions and ledger rows. Deleting it would leave those records
    pointing at nothing, so the count is what decides whether removal is allowed.
    A code typed by mistake a moment ago has none of this and can safely go.
    """
    from app.modules.inventory_ledger.models import InventoryLedgerRow
    from app.modules.production.models import ProductionLine, ProductionOrder
    from app.modules.purchases.models import PurchaseLine
    from app.modules.sales.models import SalesLine

    references = (
        (InventoryLedgerRow, InventoryLedgerRow.item_code),
        (PurchaseLine, PurchaseLine.item_code),
        (SalesLine, SalesLine.item_code),
        (ProductionOrder, ProductionOrder.output_item_code),
        (ProductionLine, ProductionLine.component_code),
        (BomComponent, BomComponent.parent_code),
        (BomComponent, BomComponent.component_code),
    )
    total = 0
    for model, column in references:
        total += db.execute(
            select(func.count()).select_from(model).where(column == code)
        ).scalar_one()
    return total


def delete_item(db: Session, item: Item) -> None:
    """Remove an item row."""
    db.delete(item)
    db.flush()
