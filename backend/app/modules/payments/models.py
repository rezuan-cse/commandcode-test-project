"""Money received from customers, and money paid to suppliers.

One table for both directions. Everything about them is the same — a partner, an
amount, a date, the account the money moved through, and the list of invoices it
settles — and only the accounts and the sign differ.

A payment carries its **amount** and a set of **allocations**. The allocations may
settle one invoice, several, or none at all:

* an allocation against an invoice is the ordinary case — a customer pays a bill;
* no allocations at all means the money is **on account**, credit held against the
  partner until there is an invoice to put it against. That is what a deposit or an
  advance is, and recording it here rather than as a manual journal is what keeps
  it attached to the partner, so their balance is right.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, enum_col
from app.core.enums import PaymentDirection
from app.core.mixins import ReversibleMixin


class Payment(ReversibleMixin, Base):
    """A receipt from a customer, or a payment to a supplier."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    voucher_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    pay_date: Mapped[date] = mapped_column(Date, nullable=False)
    direction: Mapped[PaymentDirection] = mapped_column(
        enum_col(PaymentDirection), nullable=False
    )

    # Who the money belongs to. Required: money that is not attached to a partner
    # cannot be balanced against anything, which is the whole point of recording it
    # here rather than as a journal entry.
    party_code: Mapped[str] = mapped_column(
        ForeignKey("parties.code"), nullable=False, index=True
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    # The cash or bank account the money moved through. Configurable, so a second
    # bank account is a setting rather than a code change.
    money_account: Mapped[str] = mapped_column(String(8), nullable=False)

    reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    memo: Mapped[str | None] = mapped_column(String(200), nullable=True)

    journal_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("journal_entries.id"), nullable=True
    )
    posted_by: Mapped[str] = mapped_column(String(80), default="system", nullable=False)
    posted_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    allocations: Mapped[list["PaymentAllocation"]] = relationship(
        back_populates="payment", cascade="all, delete-orphan", lazy="selectin"
    )


class PaymentAllocation(Base):
    """How much of a payment settles a particular invoice.

    Two separate nullable links rather than one polymorphic pair, so the database
    itself guarantees that an allocation points at a real sale or purchase. An
    allocation is not a posting — it is part of the payment — so the paid and
    outstanding figures exclude allocations whose payment has been reversed, which
    is what puts an invoice back to unpaid when a cheque bounces.
    """

    __tablename__ = "payment_allocations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sale_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("sales_orders.id"), nullable=True, index=True
    )
    purchase_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchase_orders.id"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    payment: Mapped[Payment] = relationship(back_populates="allocations")
