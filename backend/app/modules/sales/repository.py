"""All database queries for sales orders live here."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.sales.models import SalesOrder


def list_orders(db: Session, limit: int = 200) -> list[SalesOrder]:
    """List sales orders, newest first."""
    stmt = (
        select(SalesOrder)
        .order_by(SalesOrder.sale_date.desc(), SalesOrder.id.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def get_order(db: Session, order_id: int) -> SalesOrder | None:
    """Fetch one sales order."""
    return db.get(SalesOrder, order_id)


def add_order(db: Session, order: SalesOrder) -> SalesOrder:
    """Persist a sales order and its lines."""
    db.add(order)
    db.flush()
    return order
