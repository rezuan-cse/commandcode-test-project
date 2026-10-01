"""Thin HTTP routes for receipts and payments."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.enums import PaymentDirection
from app.core.schemas import ReversalRequest
from app.modules.payments import service
from app.modules.payments.schemas import (
    AllocateIn,
    OutstandingInvoice,
    PaymentIn,
    PaymentOut,
    PaymentPreview,
)
from app.modules.users_roles.service import Principal, require

router = APIRouter(prefix="/payments", tags=["payments"])

CAN_READ = Depends(require("payments", write=False))


@router.get("", response_model=list[PaymentOut], dependencies=[CAN_READ])
def list_payments(
    party_code: str | None = Query(default=None),
    direction: PaymentDirection | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[PaymentOut]:
    """List receipts and payments, newest first."""
    return service.list_payments(db, party_code=party_code, direction=direction)


@router.get("/outstanding", response_model=list[OutstandingInvoice], dependencies=[CAN_READ])
def outstanding(
    kind: str | None = Query(default=None, pattern="^(sale|purchase)$"),
    party_code: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[OutstandingInvoice]:
    """Every invoice that is not fully settled.

    Declared before ``/{payment_id}`` so the path is not read as an id.
    """
    return service.outstanding(db, kind=kind, party_code=party_code)


@router.get("/money-accounts", response_model=list[str], dependencies=[CAN_READ])
def money_accounts(db: Session = Depends(get_db)) -> list[str]:
    """The cash and bank accounts money may move through."""
    return service.money_accounts(db)


@router.post("/preview", response_model=PaymentPreview)
def preview_payment(
    payload: PaymentIn,
    principal: Principal = Depends(require("payments", write=True)),
    db: Session = Depends(get_db),
) -> PaymentPreview:
    """Show the journal entry and how the money would be applied."""
    return service.preview(db, payload)


@router.post("", response_model=PaymentOut, status_code=201)
def post_payment(
    payload: PaymentIn,
    principal: Principal = Depends(require("payments", write=True)),
    db: Session = Depends(get_db),
) -> PaymentOut:
    """Record a receipt from a customer or a payment to a supplier.

    With no allocations the money is held on account for that partner, which is
    what a deposit or an advance is.
    """
    return service.post(db, payload, posted_by=principal.user.email)


@router.get("/{payment_id}", response_model=PaymentOut, dependencies=[CAN_READ])
def get_payment(payment_id: int, db: Session = Depends(get_db)) -> PaymentOut:
    """Fetch one receipt or payment with the invoices it settles."""
    return service.get_payment_out(db, payment_id)


@router.post("/{payment_id}/allocate", response_model=PaymentOut)
def allocate(
    payment_id: int,
    payload: AllocateIn,
    principal: Principal = Depends(require("payments", write=True)),
    db: Session = Depends(get_db),
) -> PaymentOut:
    """Put an on-account balance against invoices later.

    No journal entry is written: the money already moved, and this only decides
    which invoices it settles.
    """
    return service.allocate(db, payment_id, payload.allocations)


@router.post("/{payment_id}/reverse", response_model=PaymentOut)
def reverse_payment(
    payment_id: int,
    payload: ReversalRequest,
    principal: Principal = Depends(require("payments", write=True)),
    db: Session = Depends(get_db),
) -> PaymentOut:
    """Undo a receipt or payment — a bounced cheque, say.

    The invoices it had settled become unpaid again; nothing is edited or deleted.
    """
    return service.reverse(
        db,
        payment_id,
        reason=payload.reason,
        reversal_date=payload.reversal_date,
        posted_by=principal.user.email,
    )
