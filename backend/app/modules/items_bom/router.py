"""Thin HTTP routes for items and BOM."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.items_bom import service
from app.modules.items_bom.schemas import (
    BomComponentIn,
    BomComponentOut,
    BomExplosionOut,
    ItemIn,
    ItemOut,
    ItemUpdate,
)
from app.modules.users_roles.service import Principal, require

router = APIRouter(prefix="/items", tags=["items-bom"])

CAN_READ = Depends(require("items_bom", write=False))


@router.get("", response_model=list[ItemOut], dependencies=[CAN_READ])
def list_items(
    search: str | None = Query(default=None), db: Session = Depends(get_db)
) -> list[ItemOut]:
    """List items with live quantity and average cost."""
    return service.list_items(db, search=search)


@router.post("", response_model=ItemOut, status_code=201)
def create_item(
    payload: ItemIn,
    principal: Principal = Depends(require("items_bom", write=True)),
    db: Session = Depends(get_db),
) -> ItemOut:
    """Add an item to the master."""
    return service.create_item(db, payload)


@router.patch("/{code}", response_model=ItemOut)
def update_item(
    code: str,
    payload: ItemUpdate,
    principal: Principal = Depends(require("items_bom", write=True)),
    db: Session = Depends(get_db),
) -> ItemOut:
    """Correct an item's name, category, segment, unit or active flag."""
    return service.update_item(db, code, payload)


@router.delete("/{code}")
def delete_item(
    code: str,
    principal: Principal = Depends(require("items_bom", write=True)),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Remove an item that no transaction or BOM refers to.

    Refused once the item has any history; set it inactive instead.
    """
    service.delete_item(db, code)
    return {"message": f"Item {code} deleted"}


@router.get("/{code}", response_model=ItemOut, dependencies=[CAN_READ])
def get_item(code: str, db: Session = Depends(get_db)) -> ItemOut:
    """Fetch one item."""
    return service.get_item_out(db, code)


@router.get("/{code}/bom", response_model=list[BomComponentOut], dependencies=[CAN_READ])
def list_bom(code: str, db: Session = Depends(get_db)) -> list[BomComponentOut]:
    """List an item's direct BOM components."""
    return service.list_components(db, code)


@router.post("/{code}/bom", response_model=list[BomComponentOut], status_code=201)
def add_bom_component(
    code: str,
    payload: BomComponentIn,
    principal: Principal = Depends(require("items_bom", write=True)),
    db: Session = Depends(get_db),
) -> list[BomComponentOut]:
    """Add a component to an item's recipe, or correct its quantity.

    Refused if either item is unknown, if the component is the parent itself, or
    if the edge would close a loop. Returns the parent's full recipe.
    """
    return service.add_component(db, code, payload)


@router.delete("/{code}/bom/{component_code}", response_model=list[BomComponentOut])
def remove_bom_component(
    code: str,
    component_code: str,
    principal: Principal = Depends(require("items_bom", write=True)),
    db: Session = Depends(get_db),
) -> list[BomComponentOut]:
    """Remove one component from an item's recipe. Returns the remaining recipe."""
    return service.remove_component(db, code, component_code)


@router.get("/{code}/explode", response_model=BomExplosionOut, dependencies=[CAN_READ])
def explode_bom(
    code: str, qty: Decimal = Query(gt=0), db: Session = Depends(get_db)
) -> BomExplosionOut:
    """Explode a multi-stage BOM for a target quantity."""
    return service.explode(db, code, qty)
