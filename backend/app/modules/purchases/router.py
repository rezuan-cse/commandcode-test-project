"""Thin HTTP routes for purchase entry."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.purchases import service
from app.modules.purchases.schemas import (
    PurchasePostResult,
    PurchasePreview,
    PurchaseRequest,
    PurchaseOut,
)
from app.modules.users_roles.service import require

router = APIRouter(prefix="/purchases", tags=["purchases"])

CAN_READ = Depends(require("sales_purchase", write=False))
CAN_WRITE = Depends(require("sales_purchase", write=True))


@router.get("", response_model=list[PurchaseOut], dependencies=[CAN_READ])
def list_orders(db: Session = Depends(get_db)) -> list[PurchaseOut]:
    """List posted purchase orders."""
    return service.list_orders(db)


@router.post("/preview", response_model=PurchasePreview, dependencies=[CAN_WRITE])
def preview_purchase(
    payload: PurchaseRequest, db: Session = Depends(get_db)
) -> PurchasePreview:
    """Preview a purchase and its journal entry."""
    return service.preview(db, payload)


@router.post("", response_model=PurchasePostResult, status_code=201, dependencies=[CAN_WRITE])
def post_purchase(
    payload: PurchaseRequest, db: Session = Depends(get_db)
) -> PurchasePostResult:
    """Post a purchase atomically."""
    return service.post(db, payload)
