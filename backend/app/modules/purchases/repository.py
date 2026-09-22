"""All database queries for purchase orders live here."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.purchases.models import PurchaseOrder


def list_orders(db: Session, limit: int = 200) -> list[PurchaseOrder]:
    """List purchase orders, newest first."""
    stmt = (
        select(PurchaseOrder)
        .order_by(PurchaseOrder.purchase_date.desc(), PurchaseOrder.id.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def get_order(db: Session, order_id: int) -> PurchaseOrder | None:
    """Fetch one purchase order with its lines loaded."""
    stmt = (
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .where(PurchaseOrder.id == order_id)
    )
    return db.execute(stmt).scalar_one_or_none()


def add_order(db: Session, order: PurchaseOrder) -> PurchaseOrder:
    """Persist a purchase order and its lines."""
    db.add(order)
    db.flush()
    return order
