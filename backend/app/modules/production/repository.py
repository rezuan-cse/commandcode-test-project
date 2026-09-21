"""All database queries for production orders live here."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.production.models import ProductionOrder


def list_orders(db: Session, limit: int = 200) -> list[ProductionOrder]:
    """List production orders, newest first, with lines eagerly loaded."""
    stmt = (
        select(ProductionOrder)
        .order_by(ProductionOrder.production_date.desc(), ProductionOrder.id.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def get_order(db: Session, order_id: int) -> ProductionOrder | None:
    """Fetch one production order."""
    return db.get(ProductionOrder, order_id)


def add_order(db: Session, order: ProductionOrder) -> ProductionOrder:
    """Persist a production order and its lines."""
    db.add(order)
    db.flush()
    return order
