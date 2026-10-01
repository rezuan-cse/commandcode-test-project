"""Pydantic schemas for receipts and payments."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.clock import LocalDateTime
from app.core.enums import PaymentDirection


class AllocationIn(BaseModel):
    """One invoice a payment settles, and how much of it."""

    # Exactly one of these is set. Both absent means the money is on account.
    sale_order_id: int | None = None
    purchase_order_id: int | None = None
    amount: Decimal = Field(gt=0)


class PaymentIn(BaseModel):
    """Payload for previewing or posting a receipt or payment.

    ``allocations`` may be empty: that records money received (or paid) that is not
    against any invoice, which is what a deposit or an advance is.
    """

    direction: PaymentDirection
    party_code: str = Field(min_length=1)
    pay_date: date
    amount: Decimal = Field(gt=0)
    money_account: str = Field(min_length=1, max_length=8)
    reference: str | None = Field(default=None, max_length=64)
    memo: str | None = Field(default=None, max_length=200)
    allocations: list[AllocationIn] = Field(default_factory=list)


class AllocateIn(BaseModel):
    """Payload for putting an on-account balance against invoices later."""

    allocations: list[AllocationIn] = Field(min_length=1)


class AllocationOut(BaseModel):
    """One invoice a payment settles, with enough to name it on screen."""

    sale_order_id: int | None = None
    purchase_order_id: int | None = None
    invoice_no: str
    invoice_date: date
    invoice_total: Decimal
    amount: Decimal


class JournalLinePreviewOut(BaseModel):
    """A journal line as the preview shows it."""

    account_code: str
    account_name: str
    debit: Decimal
    credit: Decimal
    narration: str


class PaymentPreview(BaseModel):
    """What posting this payment will do, before it is committed."""

    direction: PaymentDirection
    party_code: str
    party_name: str
    amount: Decimal
    allocated: Decimal
    on_account: Decimal
    journal_lines: list[JournalLinePreviewOut]


class PaymentOut(BaseModel):
    """A posted receipt or payment."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    voucher_no: str
    pay_date: date
    direction: PaymentDirection
    party_code: str
    party_name: str = ""
    amount: Decimal
    money_account: str
    reference: str | None = None
    memo: str | None = None
    journal_entry_id: int | None = None
    posted_by: str
    posted_at: LocalDateTime | None = None
    allocated: Decimal = Decimal("0")
    on_account: Decimal = Decimal("0")
    allocations: list[AllocationOut] = Field(default_factory=list)
    is_reversed: bool = False
    reversed_by: str | None = None
    reversal_reason: str | None = None
    reversed_at: LocalDateTime | None = None


class OutstandingInvoice(BaseModel):
    """An unpaid or partly paid invoice, as the outstanding list shows it."""

    kind: str
    invoice_id: int
    invoice_no: str
    invoice_date: date
    party_code: str | None = None
    party_name: str
    total: Decimal
    paid: Decimal
    outstanding: Decimal
    is_reversed: bool = False
