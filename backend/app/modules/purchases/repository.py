"""All database queries for purchase orders live here."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.purchases.models import PurchaseOrder


def list_orders(db: Session, limit: int = 200) -> list[PurchaseOrder]:
    """List purchase orders, newest first."""
    stmt = (
        select(PurchaseOrder)
        .order_by(PurchaseOrder.purchase_date.desc(), PurchaseOrder.id.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def add_order(db: Session, order: PurchaseOrder) -> PurchaseOrder:
    """Persist a purchase order and its lines."""
    db.add(order)
    db.flush()
    return order
