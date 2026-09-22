"""Weighted-average costing engine and inventory ledger writes.

This module owns the single source of truth for an item's quantity, value, and
average cost. Every stock movement in the system goes through
:func:`record_movement`, which is why the production and sales modules call it
rather than writing ledger rows directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import INCREASING_MOVEMENTS, MovementType
from app.core.exceptions import InsufficientStockError, NotFoundError
from app.core.money import money, rate, to_decimal, ZERO
from app.modules.inventory_ledger import repository
from app.modules.inventory_ledger.models import InventoryLedgerRow


@dataclass(frozen=True)
class ItemPosition:
    """An item's current stock position."""

    qty: Decimal
    value: Decimal
    avg_cost: Decimal

    @property
    def is_negative(self) -> bool:
        """True when the position is short, which should never persist."""
        return self.qty < 0


def position(db: Session, item_code: str, *, as_of: date | None = None) -> ItemPosition:
    """Derive an item's position from its ledger history.

    The most recent row's running balance already encodes the result, so this is
    an O(1) read once rows exist.
    """
    rows = repository.rows_for_item(db, item_code, as_of=as_of)
    if not rows:
        return ItemPosition(qty=ZERO, value=ZERO, avg_cost=ZERO)
    last = rows[-1]
    return ItemPosition(
        qty=money(last.balance_qty),
        value=money(last.balance_value),
        avg_cost=rate(last.avg_cost),
    )


def _next_average(old_qty: Decimal, old_value: Decimal, in_qty: Decimal, in_value: Decimal) -> Decimal:
    """Weighted average after a receipt. Falls back to the incoming cost."""
    new_qty = old_qty + in_qty
    if new_qty == 0:
        return ZERO
    return rate((old_value + in_value) / new_qty)


def record_movement(
    db: Session,
    *,
    item_code: str,
    movement_type: MovementType,
    movement_date: date,
    qty: Decimal,
    reference: str | None = None,
    unit_cost: Decimal | None = None,
    value: Decimal | None = None,
    journal_entry_id: int | None = None,
) -> InventoryLedgerRow:
    """Append one movement and recompute the running balance and average cost.

    ``movement_type`` decides direction: Opening, Purchase-In, Production-In and
    Reversal-In increase stock; everything else decreases it.

    ``value`` sets the total for the movement explicitly, which matters when it
    is not simply quantity times a unit cost — a reversal restores stock at
    exactly the value it left at, so the arithmetic unwinds precisely. Supply
    ``unit_cost`` instead when the movement is priced at a known rate.
    """
    from app.modules.items_bom import repository as items_repo

    if items_repo.get_item(db, item_code) is None:
        raise NotFoundError(f"Item {item_code} not found")

    qty = money(qty)
    current = position(db, item_code)
    is_increase = movement_type in INCREASING_MOVEMENTS

    if is_increase:
        in_value = money(to_decimal(value) if value is not None else to_decimal(unit_cost) * qty)
        new_qty = money(current.qty + qty)
        new_value = money(current.value + in_value)
        new_avg = _next_average(current.qty, current.value, qty, in_value)
        row = InventoryLedgerRow(
            movement_date=movement_date,
            item_code=item_code,
            movement_type=movement_type,
            reference=reference,
            in_qty=qty,
            in_value=in_value,
            out_qty=ZERO,
            out_value=ZERO,
            balance_qty=new_qty,
            balance_value=new_value,
            avg_cost=rate(new_avg),
            journal_entry_id=journal_entry_id,
        )
    else:
        if qty > current.qty:
            raise InsufficientStockError(
                f"Cannot take {qty} of {item_code}: only {current.qty} on hand"
            )
        cost = value if value is not None else money(current.avg_cost * qty)
        cost = money(cost)
        new_qty = money(current.qty - qty)
        new_value = money(current.value - cost)
        # The average is always the remaining value divided by the remaining
        # quantity. For a normal issue at average cost this is unchanged; it
        # only moves when a historical row recorded its own out-value.
        carried_avg = rate(new_value / new_qty) if new_qty != 0 else current.avg_cost
        row = InventoryLedgerRow(
            movement_date=movement_date,
            item_code=item_code,
            movement_type=movement_type,
            reference=reference,
            in_qty=ZERO,
            in_value=ZERO,
            out_qty=qty,
            out_value=cost,
            balance_qty=new_qty,
            balance_value=new_value,
            avg_cost=rate(carried_avg),
            journal_entry_id=journal_entry_id,
        )

    return repository.add_row(db, row)


def cost_of(db: Session, item_code: str, qty: Decimal) -> Decimal:
    """Value a quantity at the item's current weighted-average cost."""
    return money(position(db, item_code).avg_cost * money(qty))


def list_rows(
    db: Session, *, item_code: str | None = None, as_of: date | None = None, limit: int = 500
) -> list[InventoryLedgerRow]:
    """List ledger rows for one item or across all items."""
    if item_code:
        return repository.rows_for_item(db, item_code, as_of=as_of)
    return repository.all_rows(db, as_of=as_of, limit=limit)
