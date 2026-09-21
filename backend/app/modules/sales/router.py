"""Thin HTTP routes for sales entry."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.sales import service
from app.modules.sales.schemas import SalePostResult, SalePreview, SaleRequest, SaleOut
from app.modules.users_roles.service import require

router = APIRouter(prefix="/sales", tags=["sales"])

CAN_READ = Depends(require("sales_purchase", write=False))
CAN_WRITE = Depends(require("sales_purchase", write=True))


@router.get("", response_model=list[SaleOut], dependencies=[CAN_READ])
def list_orders(db: Session = Depends(get_db)) -> list[SaleOut]:
    """List posted sales orders."""
    return service.list_orders(db)


@router.post("/preview", response_model=SalePreview, dependencies=[CAN_WRITE])
def preview_sale(payload: SaleRequest, db: Session = Depends(get_db)) -> SalePreview:
    """Preview revenue, COGS, margin, and the journal entry for a sale."""
    return service.preview(db, payload)


@router.post("", response_model=SalePostResult, status_code=201, dependencies=[CAN_WRITE])
def post_sale(payload: SaleRequest, db: Session = Depends(get_db)) -> SalePostResult:
    """Post a sale atomically."""
    return service.post(db, payload)
