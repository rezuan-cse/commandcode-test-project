"""Business logic for purchase entry, including atomic auto-posting.

Mirror image of sales: stock rises at the purchase cost (updating the item's
weighted average), and a balanced journal entry debits inventory while crediting
either the supplier payable or cash.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.accounting import (
    DEFAULT_AP_IMPORT_ACCOUNT,
    DEFAULT_AP_LOCAL_ACCOUNT,
    DEFAULT_BANK_ACCOUNT,
    inventory_account,
)
from app.core.enums import JournalSource, MovementType
from app.core.exceptions import NotFoundError, StockMovedError
from app.core.money import money, to_decimal, ZERO
from app.core.numbering import next_voucher
from app.modules.accounts import repository as accounts_repo
from app.modules.inventory_ledger import repository as ledger_repository
from app.modules.inventory_ledger import service as ledger
from app.modules.items_bom import repository as items_repo
from app.modules.journal_entries import repository as journal_repo
from app.modules.journal_entries import service as journal_service
from app.modules.journal_entries.models import JournalEntry
from app.modules.journal_entries.schemas import JournalLineIn
from app.modules.parties import service as parties_service
from app.modules.production.schemas import JournalLinePreview
from app.modules.purchases import repository
from app.modules.purchases.models import PurchaseLine, PurchaseOrder
from app.modules.purchases.schemas import (
    PurchaseLinePreview,
    PurchasePostResult,
    PurchasePreview,
    PurchaseRequest,
    PurchaseOut,
)
from app.modules.vat_tax import service as vat_tax


def _account_name(db: Session, code: str) -> str:
    """Look up an account's display name, falling back to its code."""
    account = accounts_repo.get_account(db, code)
    return account.name_en if account else code


def _value_lines(db: Session, payload: PurchaseRequest) -> list[PurchaseLinePreview]:
    """Value each received line and project the resulting average cost."""
    priced: list[PurchaseLinePreview] = []
    for line in payload.lines:
        item = items_repo.get_item(db, line.item_code)
        if item is None:
            raise NotFoundError(f"Item {line.item_code} not found")
        position = ledger.position(db, item.code)
        qty = money(line.qty)
        unit_cost = to_decimal(line.unit_cost)
        value = money(qty * unit_cost)
        new_qty = position.qty + qty
        after = (position.value + value) / new_qty if new_qty else ZERO
        priced.append(
            PurchaseLinePreview(
                item_code=item.code,
                item_name=item.name,
                qty=qty,
                unit_cost=unit_cost,
                line_value=value,
                vat_amount=vat_tax.purchase_vat(
                    db, segment=item.segment.value, item_code=item.code, net=value
                ),
                on_hand_before=position.qty,
                avg_cost_before=position.avg_cost,
                avg_cost_after=money(after),
            )
        )
    return priced


def _journal_preview(
    db: Session, lines: list[PurchaseLinePreview], order_no: str, is_credit: bool
) -> list[JournalLinePreview]:
    """Debit each item's inventory account and credit payable or bank."""
    entries: list[JournalLinePreview] = []
    for line in lines:
        item = items_repo.get_item(db, line.item_code)
        if item is None:
            continue
        account = inventory_account(item.category)
        entries.append(
            JournalLinePreview(
                account_code=account,
                account_name=_account_name(db, account),
                segment=item.segment.value,
                debit=line.line_value,
                credit=ZERO,
                narration=f"Purchase {order_no}: {line.item_code} received",
            )
        )

    total = money(sum((line.line_value for line in lines), ZERO))
    vat_total = money(sum((line.vat_amount for line in lines), ZERO))
    credit_account = (
        DEFAULT_AP_LOCAL_ACCOUNT if is_credit else DEFAULT_BANK_ACCOUNT
    )
    if vat_total > 0:
        input_vat = vat_tax.input_account(db)
        entries.append(
            JournalLinePreview(
                account_code=input_vat,
                account_name=_account_name(db, input_vat),
                segment="Shared",
                debit=vat_total,
                credit=ZERO,
                narration=f"Input VAT on purchase {order_no}",
            )
        )
    entries.append(
        JournalLinePreview(
            account_code=credit_account,
            account_name=_account_name(db, credit_account),
            segment="Shared",
            debit=ZERO,
            credit=money(total + vat_total),
            narration=f"Purchase {order_no} {'on credit' if is_credit else 'paid'}",
        )
    )
    return entries


def _assemble(
    db: Session,
    payload: PurchaseRequest,
    lines: list[PurchaseLinePreview],
    order_no: str,
) -> PurchasePreview:
    """Assemble the purchase value and journal preview."""
    total = money(sum((line.line_value for line in lines), ZERO))
    vat_total = money(sum((line.vat_amount for line in lines), ZERO))
    journal_lines = _journal_preview(db, lines, order_no, payload.is_credit)
    debits = money(sum((line.debit for line in journal_lines), ZERO))
    credits = money(sum((line.credit for line in journal_lines), ZERO))
    return PurchasePreview(
        supplier=payload.supplier,
        lines=lines,
        total_value=total,
        vat_total=vat_total,
        grand_total=money(total + vat_total),
        journal_lines=journal_lines,
        balanced=debits == credits,
        can_post=True,
        warnings=[],
    )


def preview(db: Session, payload: PurchaseRequest) -> PurchasePreview:
    """Preview a purchase without changing anything."""
    return _assemble(db, payload, _value_lines(db, payload), "PUR-NEW")


def _party_name(db: Session, party_code: str | None, fallback: str) -> str:
    """The name to record: the party's own, when one was chosen.

    See the note on the sales version: taking the name from the record keeps the
    displayed name and the identity behind it from drifting apart.
    """
    if not party_code:
        return fallback
    return parties_service.get_party(db, party_code).name


def post(
    db: Session, payload: PurchaseRequest, *, posted_by: str = "system"
) -> PurchasePostResult:
    """Post a purchase atomically: raise stock, credit payable or bank.

    ``posted_by`` is the signed-in user, supplied by the router out of the
    session rather than trusted from the payload.
    """
    try:
        priced = _value_lines(db, payload)
        order_no = next_voucher(
            db, PurchaseOrder, "order_no", "PUR", also=[(JournalEntry, "voucher_no")]
        )
        preview_data = _assemble(db, payload, priced, order_no)

        order = PurchaseOrder(
            order_no=order_no,
            purchase_date=payload.purchase_date,
            supplier=_party_name(db, payload.party_code, payload.supplier),
            party_code=payload.party_code,
            is_credit=payload.is_credit,
            total_value=preview_data.total_value,
            vat_total=preview_data.vat_total,
            posted_by=posted_by,
        )
        for line in preview_data.lines:
            order.lines.append(
                PurchaseLine(
                    item_code=line.item_code,
                    qty=line.qty,
                    unit_cost=line.unit_cost,
                    line_value=line.line_value,
                    vat_amount=line.vat_amount,
                )
            )
        repository.add_order(db, order)

        journal_service.assert_books_open(db, payload.purchase_date)
        entry = journal_service.build_entry(
            voucher_no=order_no,
            entry_date=payload.purchase_date,
            lines=[
                JournalLineIn(
                    account_code=line.account_code,
                    segment=line.segment,
                    debit=line.debit,
                    credit=line.credit,
                    narration=line.narration,
                )
                for line in preview_data.journal_lines
            ],
            source=JournalSource.PURCHASE,
            narration=f"Auto-posted from purchase order {order_no}",
            reference=order_no,
            posted_by=posted_by,
        )
        journal_repo.add_entry(db, entry)
        order.journal_entry_id = entry.id

        for line in preview_data.lines:
            ledger.record_movement(
                db,
                item_code=line.item_code,
                movement_type=MovementType.PURCHASE_IN,
                movement_date=payload.purchase_date,
                qty=line.qty,
                unit_cost=line.unit_cost,
                reference=order_no,
                journal_entry_id=entry.id,
            )

        if payload.simulate_failure:
            raise RuntimeError("Simulated failure injected to demonstrate rollback")

        db.commit()
        return PurchasePostResult(
            order=PurchaseOut.model_validate(order),
            preview=preview_data,
            message=f"Posted {order_no}: stock increased, journal balanced",
        )
    except Exception:
        db.rollback()
        raise


def list_orders(db: Session, limit: int = 200) -> list[PurchaseOrder]:
    """List posted purchase orders."""
    return repository.list_orders(db, limit=limit)


def get_order(db: Session, order_id: int) -> PurchaseOrder:
    """Fetch one posted purchase with its lines, or raise :class:`NotFoundError`."""
    order = repository.get_order(db, order_id)
    if order is None:
        raise NotFoundError(f"Purchase {order_id} not found")
    return order


def _assert_items_untouched(db: Session, order: PurchaseOrder) -> None:
    """Refuse when an item has moved since the purchase.

    A reversal takes the goods back out at exactly the value they came in at. If
    the item has been sold, consumed or topped up since, subtracting that old
    value leaves what remains valued at a figure that never existed — the average
    drifts. Example: hold 100 kg at 20, buy 100 kg at 25 (200 kg at 22.50),
    consume 60 kg (140 kg at 22.50), then reverse the purchase. Removing 2,500
    leaves 40 kg carried at 16.25, though those 40 kg cost 20.

    The later transactions have to be reversed first. That puts the item back
    where it was when this purchase was posted, and the reversal is then exact.
    """
    for line in order.lines:
        purchased = ledger_repository.movement_for(db, line.item_code, order.order_no)
        if purchased is None:
            # Imported history has no ledger row to compare against; the quantity
            # guard in record_movement still protects the reversal.
            continue
        current = ledger.position(db, line.item_code)
        if (
            current.qty != money(purchased.balance_qty)
            or current.value != money(purchased.balance_value)
        ):
            raise StockMovedError(
                f"{line.item_code} has moved since this purchase "
                f"({money(purchased.balance_qty)} on hand then, {current.qty} now). "
                f"Reverse the later transactions first."
            )


def reverse(
    db: Session,
    order_id: int,
    *,
    reason: str,
    posted_by: str,
    reversal_date: date | None = None,
    bypass_approval: bool = False,
    requested_by: str | None = None,
) -> PurchaseOrder:
    """Undo a posted purchase, atomically.

    The stock goes back out at exactly the price paid, and the journal entry is
    mirrored, so the payable or the bank credit unwinds with it.

    Refused while the item has moved since the purchase — sold, consumed or topped
    up. Taking the purchase back out at its original value would leave what
    remains valued at a figure that never existed. Reverse the later transactions
    first, and the reversal is exact.
    """
    order = get_order(db, order_id)
    _assert_items_untouched(db, order)
    if not bypass_approval:
        from app.modules.approvals import service as approvals

        approvals.gate(
            db,
            source_type="purchase",
            source_id=order.id,
            action="reverse",
            amount=order.total_value,
            reason=reason,
            requested_by=requested_by or posted_by,
        )
    when = reversal_date or order.purchase_date

    try:
        entry = journal_service.reverse_for_transaction(
            db, order, reason=reason, posted_by=posted_by, reversal_date=when
        )
        for line in order.lines:
            ledger.record_movement(
                db,
                item_code=line.item_code,
                movement_type=MovementType.REVERSAL_OUT,
                movement_date=when,
                qty=line.qty,
                reference=f"{order.order_no}-REV",
                value=line.line_value,
                journal_entry_id=entry.id,
            )
        db.commit()
        return order
    except Exception:
        db.rollback()
        raise
