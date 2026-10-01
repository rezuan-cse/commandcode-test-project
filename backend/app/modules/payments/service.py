"""Business logic for receipts and payments.

A payment moves money between a partner and the bank, and settles invoices if it
was given any. The rules worth stating:

* **money belongs to a partner** — that is the whole reason this is not a journal
  entry, so a balance can be worked out for a customer or supplier;
* **an invoice may be settled in full, in part, or not at all**;
* **money with no invoice to settle is held on account** for that partner, which is
  what a deposit or an advance is;
* **an invoice cannot be paid more than it is worth**, and a reversed invoice cannot
  be paid at all;
* **a receipt settles sales and a payment settles purchases** — money coming back
  from a supplier is a credit note, which is a different thing;
* **reversing a payment puts the invoices back to unpaid**, because the allocation
  rows are kept but stop counting while the payment is reversed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.core.accounting import (
    DEFAULT_AP_LOCAL_ACCOUNT,
    DEFAULT_AR_ACCOUNT,
    DEFAULT_BANK_ACCOUNT,
)
from app.core.enums import JournalSource, PaymentDirection
from app.core.exceptions import DomainError, NotFoundError
from app.core.money import money, ZERO
from app.core.numbering import next_voucher
from app.modules.accounts import repository as accounts_repo
from app.modules.journal_entries import repository as journal_repo
from app.modules.journal_entries import service as journal_service
from app.modules.journal_entries.models import JournalEntry
from app.modules.journal_entries.schemas import JournalLineIn
from app.modules.parties import service as parties_service
from app.modules.payments import repository
from app.modules.payments.models import Payment, PaymentAllocation
from app.modules.payments.schemas import (
    AllocationIn,
    AllocationOut,
    JournalLinePreviewOut,
    OutstandingInvoice,
    PaymentIn,
    PaymentOut,
    PaymentPreview,
)

# AR/AP lines are not segment-specific, exactly as on the invoices they settle —
# which is what makes a receipt net its invoice off in the ledger.
SEGMENT = "Shared"

_RECEIPT_PREFIX = "RCV"
_PAYMENT_PREFIX = "PMT"


@dataclass
class _Resolved:
    """One allocation, checked against its invoice."""

    kind: str
    invoice: object
    amount: object


def _account_name(db: Session, code: str) -> str:
    """Look up an account's display name, falling back to its code."""
    account = accounts_repo.get_account(db, code)
    return account.name_en if account else code


def money_accounts(db: Session) -> list[str]:
    """The cash and bank accounts a payment may move through.

    Configurable, so opening a second bank account is a setting rather than a code
    change.
    """
    from app.modules.settings import service as settings_service

    value = settings_service.get_json(db, "payments.money_accounts")
    if isinstance(value, list):
        codes = [str(item) for item in value if str(item).strip()]
        if codes:
            return codes
    return [DEFAULT_BANK_ACCOUNT]


def _assert_money_account(db: Session, code: str) -> None:
    allowed = money_accounts(db)
    if code not in allowed:
        raise DomainError(
            f"{code} is not one of the accounts money may move through "
            f"({', '.join(allowed)}). Change the list in Configuration."
        )


def _assert_direction_fits(db: Session, direction: PaymentDirection, party) -> None:
    """A receipt needs a customer, a payment needs a supplier."""
    if direction is PaymentDirection.RECEIPT and party.kind.value == "Supplier":
        raise DomainError(
            f"{party.name} is recorded as a supplier only, so money cannot be "
            f"received from them. Change the record's type to include Customer, or "
            f"record a payment instead."
        )
    if direction is PaymentDirection.PAYMENT and party.kind.value == "Customer":
        raise DomainError(
            f"{party.name} is recorded as a customer only, so money cannot be paid "
            f"to them. Change the record's type to include Supplier, or record a "
            f"receipt instead."
        )


def _invoice_total(kind: str, invoice) -> object:
    """What the invoice was worth, matching what was posted to the ledger."""
    if kind == "sale":
        return money(invoice.revenue + invoice.vat_total)
    return money(invoice.total_value + invoice.vat_total)


def _load_invoice(db: Session, kind: str, invoice_id: int):
    if kind == "sale":
        from app.modules.sales import repository as sales_repo

        invoice = sales_repo.get_order(db, invoice_id)
        if invoice is None:
            raise NotFoundError(f"Sale {invoice_id} not found")
        return invoice
    from app.modules.purchases import repository as purchases_repo

    invoice = purchases_repo.get_order(db, invoice_id)
    if invoice is None:
        raise NotFoundError(f"Purchase {invoice_id} not found")
    return invoice


def _resolve(
    db: Session,
    *,
    party_code: str,
    direction: PaymentDirection,
    allocations: list[AllocationIn],
    budget,
) -> list[_Resolved]:
    """Check every allocation against its invoice, and return them resolved."""
    settled_map = repository.allocation_totals(db)
    seen: set[tuple[str, int]] = set()
    resolved: list[_Resolved] = []

    for item in allocations:
        has_sale = item.sale_order_id is not None
        has_purchase = item.purchase_order_id is not None
        if has_sale == has_purchase:
            raise DomainError(
                "Each allocation must name exactly one invoice — a sale or a "
                "purchase, not both and not neither."
            )

        kind = "sale" if has_sale else "purchase"
        if kind == "sale" and direction is not PaymentDirection.RECEIPT:
            raise DomainError(
                "A receipt settles sales invoices. Money paid to a supplier is a "
                "payment, even if it is settling a sale."
            )
        if kind == "purchase" and direction is not PaymentDirection.PAYMENT:
            raise DomainError(
                "A payment settles purchase invoices. Money received from a customer "
                "is a receipt, even if it is settling a purchase."
            )

        invoice = _load_invoice(db, kind, item.sale_order_id or item.purchase_order_id)
        key = (kind, invoice.id)
        if key in seen:
            raise DomainError(f"{invoice.order_no} is listed twice in the same payment.")
        seen.add(key)

        if getattr(invoice, "is_reversed", False):
            raise DomainError(
                f"{invoice.order_no} has been reversed, so it cannot be settled. "
                f"Reverse the payment that settled it, or settle the correct invoice."
            )

        if invoice.party_code != party_code:
            if invoice.party_code is None:
                raise DomainError(
                    f"{invoice.order_no} is not linked to a customer or supplier "
                    f"record, so money cannot be attached to it. Use Adopt existing "
                    f"names on Customers & Suppliers to link it, then settle it."
                )
            raise DomainError(
                f"{invoice.order_no} belongs to a different customer or supplier."
            )

        total = _invoice_total(kind, invoice)
        already = settled_map.get(key, ZERO)
        outstanding = money(total - already)
        amount = money(item.amount)
        if amount > outstanding:
            raise DomainError(
                f"{invoice.order_no} has {outstanding:,.2f} outstanding, so it cannot "
                f"take {amount:,.2f}."
            )
        resolved.append(_Resolved(kind=kind, invoice=invoice, amount=amount))

    allocated = money(sum((row.amount for row in resolved), ZERO))
    if allocated > budget:
        raise DomainError(
            f"The allocations total {allocated:,.2f}, which is more than the "
            f"{money(budget):,.2f} being paid."
        )
    return resolved


def _journal_lines(
    db: Session,
    *,
    direction: PaymentDirection,
    amount,
    money_account: str,
    party_name: str,
    voucher_no: str,
) -> list[JournalLineIn]:
    """The two-line entry: money moves, and the partner's balance moves with it."""
    if direction is PaymentDirection.RECEIPT:
        pairs = [
            (money_account, amount, ZERO, f"{voucher_no} received from {party_name}"),
            (DEFAULT_AR_ACCOUNT, ZERO, amount, f"{voucher_no} settles receivable"),
        ]
    else:
        pairs = [
            (DEFAULT_AP_LOCAL_ACCOUNT, amount, ZERO, f"{voucher_no} settles payable"),
            (money_account, ZERO, amount, f"{voucher_no} paid to {party_name}"),
        ]
    return [
        JournalLineIn(
            account_code=code, segment=SEGMENT, debit=debit, credit=credit, narration=text
        )
        for code, debit, credit, text in pairs
    ]


def _lines_out(db: Session, lines: list[JournalLineIn]) -> list[JournalLinePreviewOut]:
    return [
        JournalLinePreviewOut(
            account_code=line.account_code,
            account_name=_account_name(db, line.account_code),
            debit=money(line.debit),
            credit=money(line.credit),
            narration=line.narration or "",
        )
        for line in lines
    ]


def _party_names(db: Session) -> dict[str, str]:
    return {party.code: party.name for party in parties_service.list_parties(db)}


def preview(db: Session, payload: PaymentIn) -> PaymentPreview:
    """Show what posting this would do, without writing anything."""
    party = parties_service.get_party(db, payload.party_code)
    _assert_direction_fits(db, payload.direction, party)
    _assert_money_account(db, payload.money_account)

    amount = money(payload.amount)
    resolved = _resolve(
        db,
        party_code=payload.party_code,
        direction=payload.direction,
        allocations=payload.allocations,
        budget=amount,
    )
    allocated = money(sum((row.amount for row in resolved), ZERO))
    lines = _journal_lines(
        db,
        direction=payload.direction,
        amount=amount,
        money_account=payload.money_account,
        party_name=party.name,
        voucher_no="(preview)",
    )
    return PaymentPreview(
        direction=payload.direction,
        party_code=party.code,
        party_name=party.name,
        amount=amount,
        allocated=allocated,
        on_account=money(amount - allocated),
        journal_lines=_lines_out(db, lines),
    )


def post(db: Session, payload: PaymentIn, *, posted_by: str = "system") -> PaymentOut:
    """Record a receipt or payment atomically, with its allocations."""
    party = parties_service.get_party(db, payload.party_code)
    _assert_direction_fits(db, payload.direction, party)
    _assert_money_account(db, payload.money_account)

    amount = money(payload.amount)
    # Checked before anything is written, so a refused payment leaves no trace.
    resolved = _resolve(
        db,
        party_code=payload.party_code,
        direction=payload.direction,
        allocations=payload.allocations,
        budget=amount,
    )
    journal_service.assert_books_open(db, payload.pay_date)

    receipt = payload.direction is PaymentDirection.RECEIPT
    voucher_no = next_voucher(
        db,
        Payment,
        "voucher_no",
        _RECEIPT_PREFIX if receipt else _PAYMENT_PREFIX,
        also=[(JournalEntry, "voucher_no")],
    )

    payment = Payment(
        voucher_no=voucher_no,
        pay_date=payload.pay_date,
        direction=payload.direction,
        party_code=party.code,
        amount=amount,
        money_account=payload.money_account,
        reference=payload.reference,
        memo=payload.memo,
        posted_by=posted_by,
    )
    for row in resolved:
        payment.allocations.append(
            PaymentAllocation(
                sale_order_id=row.invoice.id if row.kind == "sale" else None,
                purchase_order_id=row.invoice.id if row.kind == "purchase" else None,
                amount=row.amount,
            )
        )
    repository.add_payment(db, payment)

    entry = journal_service.build_entry(
        voucher_no=voucher_no,
        entry_date=payload.pay_date,
        lines=_journal_lines(
            db,
            direction=payload.direction,
            amount=amount,
            money_account=payload.money_account,
            party_name=party.name,
            voucher_no=voucher_no,
        ),
        source=JournalSource.RECEIPT if receipt else JournalSource.PAYMENT,
        narration=(
            f"{'Receipt' if receipt else 'Payment'} {voucher_no} — {party.name}"
            + (f" — {payload.memo}" if payload.memo else "")
        ),
        reference=payload.reference,
        posted_by=posted_by,
    )
    journal_repo.add_entry(db, entry)
    payment.journal_entry_id = entry.id

    db.commit()
    return get_payment_out(db, payment.id)


def allocate(
    db: Session, payment_id: int, allocations: list[AllocationIn], *, posted_by: str = "system"
) -> PaymentOut:
    """Put an on-account balance against invoices, later.

    No journal entry is written: the money already moved when the payment was
    posted, and this only decides which invoices it settles. That is what makes a
    deposit usable once the invoice finally arrives.
    """
    payment = get_payment(db, payment_id)
    if payment.is_reversed:
        raise DomainError(
            f"{payment.voucher_no} has been reversed, so there is nothing to allocate."
        )

    allocated = _allocated_of(payment)
    credit = money(payment.amount - allocated)
    if credit <= 0:
        raise DomainError(
            f"{payment.voucher_no} is fully allocated, so it has nothing left to apply."
        )

    resolved = _resolve(
        db,
        party_code=payment.party_code,
        direction=payment.direction,
        allocations=allocations,
        budget=credit,
    )
    for row in resolved:
        payment.allocations.append(
            PaymentAllocation(
                sale_order_id=row.invoice.id if row.kind == "sale" else None,
                purchase_order_id=row.invoice.id if row.kind == "purchase" else None,
                amount=row.amount,
            )
        )
    db.commit()
    return get_payment_out(db, payment.id)


def reverse(
    db: Session,
    payment_id: int,
    *,
    reason: str,
    reversal_date: date | None = None,
    posted_by: str,
) -> PaymentOut:
    """Undo a receipt or payment — a bounced cheque, say.

    The money comes back and the entry is mirrored. The invoices it had settled
    become unpaid again on their own, because the allocations only count while the
    payment stands. Nothing is edited or deleted.
    """
    payment = get_payment(db, payment_id)
    journal_service.reverse_for_transaction(
        db,
        payment,
        reason=reason,
        posted_by=posted_by,
        reversal_date=reversal_date or payment.pay_date,
    )
    db.commit()
    return get_payment_out(db, payment.id)


def get_payment(db: Session, payment_id: int) -> Payment:
    payment = repository.get_payment(db, payment_id)
    if payment is None:
        raise NotFoundError(f"Payment {payment_id} not found")
    return payment


def _allocated_of(payment: Payment):
    """How much of this payment has been put against invoices."""
    return money(sum((money(row.amount) for row in payment.allocations), ZERO))


def _allocations_out(db: Session, payment: Payment) -> list[AllocationOut]:
    rows: list[AllocationOut] = []
    for row in payment.allocations:
        kind = "sale" if row.sale_order_id is not None else "purchase"
        invoice = _load_invoice(db, kind, row.sale_order_id or row.purchase_order_id)
        rows.append(
            AllocationOut(
                sale_order_id=row.sale_order_id,
                purchase_order_id=row.purchase_order_id,
                invoice_no=getattr(invoice, "order_no", "—"),
                invoice_date=getattr(
                    invoice, "sale_date", getattr(invoice, "purchase_date", None)
                ),
                invoice_total=_invoice_total(kind, invoice),
                amount=money(row.amount),
            )
        )
    return rows


def _to_out(db: Session, payment: Payment, names: dict[str, str] | None = None) -> PaymentOut:
    allocated = _allocated_of(payment)
    if names is None:
        names = _party_names(db)
    return PaymentOut(
        id=payment.id,
        voucher_no=payment.voucher_no,
        pay_date=payment.pay_date,
        direction=payment.direction,
        party_code=payment.party_code,
        party_name=names.get(payment.party_code, payment.party_code),
        amount=money(payment.amount),
        money_account=payment.money_account,
        reference=payment.reference,
        memo=payment.memo,
        journal_entry_id=payment.journal_entry_id,
        posted_by=payment.posted_by,
        posted_at=payment.posted_at,
        allocated=allocated,
        on_account=money(payment.amount - allocated),
        allocations=_allocations_out(db, payment),
        is_reversed=payment.is_reversed,
        reversed_by=payment.reversed_by,
        reversal_reason=payment.reversal_reason,
        reversed_at=payment.reversed_at,
    )


def get_payment_out(db: Session, payment_id: int) -> PaymentOut:
    return _to_out(db, get_payment(db, payment_id))


def list_payments(
    db: Session,
    *,
    party_code: str | None = None,
    direction: PaymentDirection | None = None,
) -> list[PaymentOut]:
    names = _party_names(db)
    return [
        _to_out(db, payment, names)
        for payment in repository.list_payments(
            db, party_code=party_code, direction=direction
        )
    ]


def outstanding(
    db: Session,
    *,
    kind: str | None = None,
    party_code: str | None = None,
) -> list[OutstandingInvoice]:
    """Every invoice that is not fully settled — the answer to "who owes what"."""
    settled = repository.allocation_totals(db)
    names = _party_names(db)
    rows: list[OutstandingInvoice] = []

    if kind in (None, "sale"):
        for order in repository.sale_invoices(db, party_code=party_code):
            total = _invoice_total("sale", order)
            paid = settled.get(("sale", order.id), ZERO)
            due = money(total - paid)
            if due <= 0:
                continue
            rows.append(
                OutstandingInvoice(
                    kind="sale",
                    invoice_id=order.id,
                    invoice_no=order.order_no,
                    invoice_date=order.sale_date,
                    party_code=order.party_code,
                    party_name=names.get(order.party_code or "", order.customer),
                    total=total,
                    paid=paid,
                    outstanding=due,
                    is_reversed=order.is_reversed,
                )
            )

    if kind in (None, "purchase"):
        for order in repository.purchase_invoices(db, party_code=party_code):
            total = _invoice_total("purchase", order)
            paid = settled.get(("purchase", order.id), ZERO)
            due = money(total - paid)
            if due <= 0:
                continue
            rows.append(
                OutstandingInvoice(
                    kind="purchase",
                    invoice_id=order.id,
                    invoice_no=order.order_no,
                    invoice_date=order.purchase_date,
                    party_code=order.party_code,
                    party_name=names.get(order.party_code or "", order.supplier),
                    total=total,
                    paid=paid,
                    outstanding=due,
                    is_reversed=order.is_reversed,
                )
            )

    rows.sort(key=lambda row: (row.invoice_date, row.invoice_no))
    return rows
