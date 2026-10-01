"""All database queries for receipts and payments live here."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import PaymentDirection
from app.core.money import money
from app.modules.payments.models import Payment, PaymentAllocation


def add_payment(db: Session, payment: Payment) -> Payment:
    """Persist a payment and its allocations."""
    db.add(payment)
    db.flush()
    return payment


def get_payment(db: Session, payment_id: int) -> Payment | None:
    """Fetch one payment with its allocations."""
    return db.get(Payment, payment_id)


def list_payments(
    db: Session,
    *,
    party_code: str | None = None,
    direction: PaymentDirection | None = None,
    limit: int = 200,
) -> list[Payment]:
    """List payments, newest first."""
    stmt = (
        select(Payment)
        .order_by(Payment.pay_date.desc(), Payment.id.desc())
        .limit(limit)
    )
    if party_code:
        stmt = stmt.where(Payment.party_code == party_code)
    if direction is not None:
        stmt = stmt.where(Payment.direction == direction)
    return list(db.execute(stmt).scalars().all())


def allocation_totals(db: Session) -> dict[tuple[str, int], Decimal]:
    """How much each invoice has been settled, keyed by ``(kind, invoice_id)``.

    Allocations belonging to a **reversed** payment are left out. A reversal undoes
    the receipt, so the invoice it had settled is unpaid again — and because the
    allocation row itself is kept rather than deleted, the history still shows that
    a payment once existed and what it covered.
    """
    totals: dict[tuple[str, int], Decimal] = {}

    sale_rows = db.execute(
        select(
            PaymentAllocation.sale_order_id,
            func.sum(PaymentAllocation.amount),
        )
        .join(Payment, Payment.id == PaymentAllocation.payment_id)
        .where(Payment.reversed_at.is_(None))
        .where(PaymentAllocation.sale_order_id.is_not(None))
        .group_by(PaymentAllocation.sale_order_id)
    ).all()
    for invoice_id, total in sale_rows:
        totals[("sale", invoice_id)] = money(total)

    purchase_rows = db.execute(
        select(
            PaymentAllocation.purchase_order_id,
            func.sum(PaymentAllocation.amount),
        )
        .join(Payment, Payment.id == PaymentAllocation.payment_id)
        .where(Payment.reversed_at.is_(None))
        .where(PaymentAllocation.purchase_order_id.is_not(None))
        .group_by(PaymentAllocation.purchase_order_id)
    ).all()
    for invoice_id, total in purchase_rows:
        totals[("purchase", invoice_id)] = money(total)

    return totals


def sale_invoices(db: Session, *, party_code: str | None = None) -> list:
    """Posted sales, oldest first, for the outstanding list."""
    from app.modules.sales.models import SalesOrder

    stmt = select(SalesOrder).order_by(SalesOrder.sale_date, SalesOrder.id)
    if party_code:
        stmt = stmt.where(SalesOrder.party_code == party_code)
    return list(db.execute(stmt).scalars().all())


def purchase_invoices(db: Session, *, party_code: str | None = None) -> list:
    """Posted purchases, oldest first, for the outstanding list."""
    from app.modules.purchases.models import PurchaseOrder

    stmt = select(PurchaseOrder).order_by(PurchaseOrder.purchase_date, PurchaseOrder.id)
    if party_code:
        stmt = stmt.where(PurchaseOrder.party_code == party_code)
    return list(db.execute(stmt).scalars().all())


def on_account_by_party(db: Session) -> dict[str, Decimal]:
    """Money held for each partner that no invoice has claimed.

    A payment with no allocations, or one whose allocations cover less than its
    amount, leaves a balance on account. Deposits and advances land here, which is
    what keeps them attached to the partner instead of lost in a journal entry.
    """
    allocated = (
        select(
            PaymentAllocation.payment_id.label("payment_id"),
            func.sum(PaymentAllocation.amount).label("settled"),
        )
        .group_by(PaymentAllocation.payment_id)
        .subquery()
    )
    rows = db.execute(
        select(
            Payment.party_code,
            func.sum(Payment.amount - func.coalesce(allocated.c.settled, 0)),
        )
        .outerjoin(allocated, allocated.c.payment_id == Payment.id)
        .where(Payment.reversed_at.is_(None))
        .group_by(Payment.party_code)
    ).all()
    return {party_code: money(total) for party_code, total in rows}
