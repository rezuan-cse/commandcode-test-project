"""Business logic for purchase entry, including atomic auto-posting.

Mirror image of sales: stock rises at the purchase cost (updating the item's
weighted average), and a balanced journal entry debits inventory while crediting
either the supplier payable or cash.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.accounting import (
    DEFAULT_AP_IMPORT_ACCOUNT,
    DEFAULT_AP_LOCAL_ACCOUNT,
    DEFAULT_BANK_ACCOUNT,
    inventory_account,
)
from app.core.enums import JournalSource, MovementType
from app.core.exceptions import NotFoundError
from app.core.money import money, to_decimal, ZERO
from app.core.numbering import next_voucher
from app.modules.accounts import repository as accounts_repo
from app.modules.inventory_ledger import service as ledger
from app.modules.items_bom import repository as items_repo
from app.modules.journal_entries import repository as journal_repo
from app.modules.journal_entries import service as journal_service
from app.modules.journal_entries.models import JournalEntry
from app.modules.journal_entries.schemas import JournalLineIn
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
    credit_account = (
        DEFAULT_AP_LOCAL_ACCOUNT if is_credit else DEFAULT_BANK_ACCOUNT
    )
    entries.append(
        JournalLinePreview(
            account_code=credit_account,
            account_name=_account_name(db, credit_account),
            segment="Shared",
            debit=ZERO,
            credit=total,
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
    journal_lines = _journal_preview(db, lines, order_no, payload.is_credit)
    debits = money(sum((line.debit for line in journal_lines), ZERO))
    credits = money(sum((line.credit for line in journal_lines), ZERO))
    return PurchasePreview(
        supplier=payload.supplier,
        lines=lines,
        total_value=total,
        journal_lines=journal_lines,
        balanced=debits == credits,
        can_post=True,
        warnings=[],
    )


def preview(db: Session, payload: PurchaseRequest) -> PurchasePreview:
    """Preview a purchase without changing anything."""
    return _assemble(db, payload, _value_lines(db, payload), "PUR-NEW")


def post(db: Session, payload: PurchaseRequest) -> PurchasePostResult:
    """Post a purchase atomically: raise stock, credit payable or bank."""
    try:
        priced = _value_lines(db, payload)
        order_no = next_voucher(
            db, PurchaseOrder, "order_no", "PUR", also=[(JournalEntry, "voucher_no")]
        )
        preview_data = _assemble(db, payload, priced, order_no)

        order = PurchaseOrder(
            order_no=order_no,
            purchase_date=payload.purchase_date,
            supplier=payload.supplier,
            is_credit=payload.is_credit,
            total_value=preview_data.total_value,
            posted_by=payload.posted_by,
        )
        for line in preview_data.lines:
            order.lines.append(
                PurchaseLine(
                    item_code=line.item_code,
                    qty=line.qty,
                    unit_cost=line.unit_cost,
                    line_value=line.line_value,
                )
            )
        repository.add_order(db, order)

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
            posted_by=payload.posted_by,
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
