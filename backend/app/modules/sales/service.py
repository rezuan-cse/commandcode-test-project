"""Business logic for sales entry, including atomic auto-posting.

A sale reduces inventory at the item's current weighted-average cost and writes
one balanced journal entry containing both sides: revenue (Dr Receivable /
Cr Sales) and cost of goods sold (Dr COGS / Cr Inventory).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.accounting import (
    cogs_account,
    DEFAULT_AR_ACCOUNT,
    inventory_account,
    sales_account,
)
from app.core.enums import JournalSource, MovementType
from app.core.exceptions import InsufficientStockError, NotFoundError
from app.core.money import money, is_zero, to_decimal, ZERO
from app.core.numbering import next_voucher
from app.modules.accounts import repository as accounts_repo
from app.modules.inventory_ledger import service as ledger
from app.modules.items_bom import repository as items_repo
from app.modules.journal_entries import repository as journal_repo
from app.modules.journal_entries import service as journal_service
from app.modules.journal_entries.models import JournalEntry
from app.modules.journal_entries.schemas import JournalLineIn
from app.modules.production.schemas import JournalLinePreview
from app.modules.sales import repository
from app.modules.sales.models import SalesLine, SalesOrder
from app.modules.sales.schemas import (
    SaleLinePreview,
    SalePostResult,
    SalePreview,
    SaleRequest,
    SaleOut,
)


def _account_name(db: Session, code: str) -> str:
    """Look up an account's display name, falling back to its code."""
    account = accounts_repo.get_account(db, code)
    return account.name_en if account else code


def _price_lines(db: Session, payload: SaleRequest) -> list[SaleLinePreview]:
    """Price each sale line at its revenue and current weighted-average cost."""
    priced: list[SaleLinePreview] = []
    for line in payload.lines:
        item = items_repo.get_item(db, line.item_code)
        if item is None:
            raise NotFoundError(f"Item {line.item_code} not found")
        position = ledger.position(db, item.code)
        qty = money(line.qty)
        unit_cost = position.avg_cost
        revenue = money(qty * to_decimal(line.sale_price))
        cogs = money(qty * unit_cost)
        margin = money(revenue - cogs)
        priced.append(
            SaleLinePreview(
                item_code=item.code,
                item_name=item.name,
                qty=qty,
                sale_price=to_decimal(line.sale_price),
                unit_cost=unit_cost,
                line_revenue=revenue,
                line_cogs=cogs,
                line_margin=margin,
                on_hand=position.qty,
                sufficient=position.qty >= qty,
                # Selling below what the item cost is allowed — a clearance sale
                # is a real thing — but it must never pass unnoticed.
                below_cost=margin < 0,
            )
        )
    return priced


def _journal_preview(
    db: Session, lines: list[SaleLinePreview], order_no: str
) -> list[JournalLinePreview]:
    """Build the two-part journal entry: revenue side and COGS side."""
    entries: list[JournalLinePreview] = []
    revenue_total = money(sum((line.line_revenue for line in lines), ZERO))

    entries.append(
        JournalLinePreview(
            account_code=DEFAULT_AR_ACCOUNT,
            account_name=_account_name(db, DEFAULT_AR_ACCOUNT),
            segment="Shared",
            debit=revenue_total,
            credit=ZERO,
            narration=f"Sale {order_no} receivable",
        )
    )

    for line in lines:
        item = items_repo.get_item(db, line.item_code)
        if item is None:
            continue
        rev_account = sales_account(item.segment)
        entries.append(
            JournalLinePreview(
                account_code=rev_account,
                account_name=_account_name(db, rev_account),
                segment=item.segment.value,
                debit=ZERO,
                credit=line.line_revenue,
                narration=f"Sale {order_no}: {line.item_code}",
            )
        )

    for line in lines:
        item = items_repo.get_item(db, line.item_code)
        if item is None:
            continue
        cogs = cogs_account(item.segment)
        inv = inventory_account(item.category)
        entries.append(
            JournalLinePreview(
                account_code=cogs,
                account_name=_account_name(db, cogs),
                segment=item.segment.value,
                debit=line.line_cogs,
                credit=ZERO,
                narration=f"COGS for {line.item_code} on {order_no}",
            )
        )
        entries.append(
            JournalLinePreview(
                account_code=inv,
                account_name=_account_name(db, inv),
                segment=item.segment.value,
                debit=ZERO,
                credit=line.line_cogs,
                narration=f"Inventory reduced for {order_no}",
            )
        )
    return entries


def _assemble(
    db: Session, payload: SaleRequest, lines: list[SaleLinePreview], order_no: str
) -> SalePreview:
    """Assemble revenue, COGS, margin, and the journal preview."""
    revenue = money(sum((line.line_revenue for line in lines), ZERO))
    cogs = money(sum((line.line_cogs for line in lines), ZERO))
    gross = money(revenue - cogs)
    margin_pct = money(gross / revenue * 100) if revenue else ZERO

    journal_lines = _journal_preview(db, lines, order_no)
    debits = money(sum((line.debit for line in journal_lines), ZERO))
    credits = money(sum((line.credit for line in journal_lines), ZERO))

    warnings = [
        f"Insufficient stock for: {line.item_code}"
        for line in lines
        if not line.sufficient
    ]
    for line in lines:
        if line.below_cost and is_zero(line.line_revenue):
            warnings.append(
                f"{line.item_code} has no sale price: this sale would give the "
                f"goods away and still record a cost of {line.line_cogs}"
            )
        elif line.below_cost:
            warnings.append(
                f"{line.item_code} is priced below cost "
                f"({line.sale_price} against a cost of {line.unit_cost}), "
                f"a loss of {abs(line.line_margin)} on this line"
            )

    return SalePreview(
        customer=payload.customer,
        lines=lines,
        revenue=revenue,
        cogs=cogs,
        gross_profit=gross,
        gross_margin_pct=margin_pct,
        journal_lines=journal_lines,
        balanced=debits == credits,
        can_post=all(line.sufficient for line in lines),
        warnings=warnings,
    )


def preview(db: Session, payload: SaleRequest) -> SalePreview:
    """Preview a sale without changing anything."""
    return _assemble(db, payload, _price_lines(db, payload), "SALE-NEW")


def _assert_available(lines: list[SaleLinePreview]) -> None:
    """Raise when any line is short of stock."""
    short = [
        f"{line.item_code} (need {line.qty}, have {line.on_hand})"
        for line in lines
        if not line.sufficient
    ]
    if short:
        raise InsufficientStockError("; ".join(short))


def post(db: Session, payload: SaleRequest) -> SalePostResult:
    """Post a sale atomically: reduce stock, recognise revenue and COGS."""
    try:
        priced = _price_lines(db, payload)
        _assert_available(priced)

        order_no = next_voucher(
            db, SalesOrder, "order_no", "SALE", also=[(JournalEntry, "voucher_no")]
        )
        preview_data = _assemble(db, payload, priced, order_no)

        order = SalesOrder(
            order_no=order_no,
            sale_date=payload.sale_date,
            customer=payload.customer,
            is_credit=payload.is_credit,
            revenue=preview_data.revenue,
            cogs=preview_data.cogs,
            posted_by=payload.posted_by,
        )
        for line in preview_data.lines:
            order.lines.append(
                SalesLine(
                    item_code=line.item_code,
                    qty=line.qty,
                    sale_price=line.sale_price,
                    unit_cost=line.unit_cost,
                    line_revenue=line.line_revenue,
                    line_cogs=line.line_cogs,
                )
            )
        repository.add_order(db, order)

        entry = journal_service.build_entry(
            voucher_no=order_no,
            entry_date=payload.sale_date,
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
            source=JournalSource.SALES,
            narration=f"Auto-posted from sales order {order_no}",
            reference=order_no,
            posted_by=payload.posted_by,
        )
        journal_repo.add_entry(db, entry)
        order.journal_entry_id = entry.id

        for line in preview_data.lines:
            ledger.record_movement(
                db,
                item_code=line.item_code,
                movement_type=MovementType.SALE_OUT,
                movement_date=payload.sale_date,
                qty=line.qty,
                reference=order_no,
                journal_entry_id=entry.id,
            )

        if payload.simulate_failure:
            raise RuntimeError("Simulated failure injected to demonstrate rollback")

        db.commit()
        return SalePostResult(
            order=SaleOut.model_validate(order),
            preview=preview_data,
            message=f"Posted {order_no}: revenue and COGS recognised, balanced",
        )
    except Exception:
        db.rollback()
        raise


def list_orders(db: Session, limit: int = 200) -> list[SalesOrder]:
    """List posted sales orders."""
    return repository.list_orders(db, limit=limit)


def get_order(db: Session, order_id: int) -> SalesOrder:
    """Fetch one posted sale with its lines, or raise :class:`NotFoundError`."""
    order = repository.get_order(db, order_id)
    if order is None:
        raise NotFoundError(f"Sale {order_id} not found")
    return order
