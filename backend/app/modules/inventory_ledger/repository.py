"""All database queries for the inventory ledger live here."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.inventory_ledger.models import InventoryLedgerRow


def rows_for_item(
    db: Session, item_code: str, *, as_of: date | None = None
) -> list[InventoryLedgerRow]:
    """Return an item's ledger rows in movement order."""
    stmt = (
        select(InventoryLedgerRow)
        .where(InventoryLedgerRow.item_code == item_code)
        .order_by(InventoryLedgerRow.movement_date, InventoryLedgerRow.id)
    )
    if as_of is not None:
        stmt = stmt.where(InventoryLedgerRow.movement_date <= as_of)
    return list(db.execute(stmt).scalars().all())


def all_rows(db: Session, *, as_of: date | None = None, limit: int = 500) -> list[InventoryLedgerRow]:
    """Return recent ledger rows across all items."""
    stmt = (
        select(InventoryLedgerRow)
        .order_by(InventoryLedgerRow.movement_date.desc(), InventoryLedgerRow.id.desc())
        .limit(limit)
    )
    if as_of is not None:
        stmt = stmt.where(InventoryLedgerRow.movement_date <= as_of)
    return list(db.execute(stmt).scalars().all())


def add_row(db: Session, row: InventoryLedgerRow) -> InventoryLedgerRow:
    """Persist a ledger row."""
    db.add(row)
    db.flush()
    return row


def add_rows(db: Session, rows: list[InventoryLedgerRow]) -> None:
    """Bulk-insert ledger rows."""
    db.add_all(rows)
    db.flush()


def existing_references(db: Session) -> set[str]:
    """Return the set of reference numbers already present (used for idempotent seeding)."""
    stmt = select(InventoryLedgerRow.reference).where(InventoryLedgerRow.reference.is_not(None))
    return {ref for (ref,) in db.execute(stmt).all() if ref}
