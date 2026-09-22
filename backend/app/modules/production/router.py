"""Thin HTTP routes for production entry."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.schemas import ReversalRequest
from app.modules.production import service
from app.modules.production.schemas import (
    ProductionPostResult,
    ProductionPreview,
    ProductionRequest,
    ProductionRunOut,
)
from app.modules.users_roles.service import require

router = APIRouter(prefix="/production", tags=["production"])

CAN_READ = Depends(require("production", write=False))
CAN_WRITE = Depends(require("production", write=True))


@router.get("", response_model=list[ProductionRunOut], dependencies=[CAN_READ])
def list_orders(db: Session = Depends(get_db)) -> list[ProductionRunOut]:
    """List posted production orders."""
    return service.list_orders(db)


@router.post(
    "/{order_id}/reverse", response_model=ProductionRunOut, dependencies=[CAN_WRITE]
)
def reverse_run(
    order_id: int,
    payload: ReversalRequest,
    db: Session = Depends(get_db),
) -> ProductionRunOut:
    """Undo a posted production run.

    The output comes back out and every component goes back in. Refused if the
    output has since been sold or used.
    """
    return service.reverse(
        db,
        order_id,
        reason=payload.reason,
        posted_by=payload.posted_by,
        reversal_date=payload.reversal_date,
    )


@router.post("/preview", response_model=ProductionPreview, dependencies=[CAN_WRITE])
def preview_run(
    payload: ProductionRequest, db: Session = Depends(get_db)
) -> ProductionPreview:
    """Preview the cost build-up and journal entry for a production run."""
    return service.preview(db, payload)


@router.post("", response_model=ProductionPostResult, status_code=201, dependencies=[CAN_WRITE])
def post_run(
    payload: ProductionRequest, db: Session = Depends(get_db)
) -> ProductionPostResult:
    """Post a production run atomically."""
    return service.post(db, payload)
