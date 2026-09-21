"""Thin HTTP routes for items and BOM."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.items_bom import service
from app.modules.items_bom.schemas import BomComponentOut, BomExplosionOut, ItemOut
from app.modules.users_roles.service import require

router = APIRouter(prefix="/items", tags=["items-bom"])

CAN_READ = Depends(require("items_bom", write=False))


@router.get("", response_model=list[ItemOut], dependencies=[CAN_READ])
def list_items(
    search: str | None = Query(default=None), db: Session = Depends(get_db)
) -> list[ItemOut]:
    """List items with live quantity and average cost."""
    return service.list_items(db, search=search)


@router.get("/{code}", response_model=ItemOut, dependencies=[CAN_READ])
def get_item(code: str, db: Session = Depends(get_db)) -> ItemOut:
    """Fetch one item."""
    return service.get_item_out(db, code)


@router.get("/{code}/bom", response_model=list[BomComponentOut], dependencies=[CAN_READ])
def list_bom(code: str, db: Session = Depends(get_db)) -> list[BomComponentOut]:
    """List an item's direct BOM components."""
    return service.list_components(db, code)


@router.get("/{code}/explode", response_model=BomExplosionOut, dependencies=[CAN_READ])
def explode_bom(
    code: str, qty: Decimal = Query(gt=0), db: Session = Depends(get_db)
) -> BomExplosionOut:
    """Explode a multi-stage BOM for a target quantity."""
    return service.explode(db, code, qty)
