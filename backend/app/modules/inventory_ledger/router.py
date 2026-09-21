"""Thin HTTP routes for the inventory ledger."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.inventory_ledger import service
from app.modules.inventory_ledger.schemas import InventoryRowOut, ItemPositionOut
from app.modules.users_roles.service import require

router = APIRouter(prefix="/inventory", tags=["inventory-ledger"])

CAN_READ = Depends(require("items_bom", write=False))


@router.get("", response_model=list[InventoryRowOut], dependencies=[CAN_READ])
def list_rows(
    item_code: str | None = Query(default=None),
    as_of: date | None = Query(default=None),
    limit: int = Query(default=500, le=2000),
    db: Session = Depends(get_db),
) -> list[InventoryRowOut]:
    """List inventory ledger movements."""
    return service.list_rows(db, item_code=item_code, as_of=as_of, limit=limit)


@router.get("/{item_code}/position", response_model=ItemPositionOut, dependencies=[CAN_READ])
def get_position(
    item_code: str, as_of: date | None = Query(default=None), db: Session = Depends(get_db)
) -> ItemPositionOut:
    """Return an item's derived quantity, value, and average cost."""
    pos = service.position(db, item_code, as_of=as_of)
    return ItemPositionOut(
        item_code=item_code, qty=pos.qty, value=pos.value, avg_cost=pos.avg_cost
    )
