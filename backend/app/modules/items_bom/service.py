"""Business logic for items and BOM, including recursive multi-stage explosion."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import DomainError, DuplicateError, NotFoundError
from app.core.money import money, to_decimal
from app.modules.inventory_ledger import service as ledger_service
from app.modules.items_bom import repository
from app.modules.items_bom.models import Item
from app.modules.items_bom.schemas import (
    BomComponentOut,
    BomExplosionLine,
    BomExplosionOut,
    ItemIn,
    ItemOut,
    ItemUpdate,
)


def _item_out(db: Session, item: Item) -> ItemOut:
    """Decorate an item with its ledger-derived quantity and cost."""
    position = ledger_service.position(db, item.code)
    return ItemOut(
        code=item.code,
        name=item.name,
        category=item.category,
        segment=item.segment,
        uom=item.uom,
        reorder_level=item.reorder_level,
        is_active=item.is_active,
        qty_on_hand=position.qty,
        avg_cost=position.avg_cost,
        value_on_hand=position.value,
    )


def list_items(db: Session, *, search: str | None = None) -> list[ItemOut]:
    """List items with live stock figures."""
    return [_item_out(db, item) for item in repository.list_items(db, search=search)]


def get_item(db: Session, code: str) -> Item:
    """Fetch an item or raise :class:`NotFoundError`."""
    item = repository.get_item(db, code)
    if item is None:
        raise NotFoundError(f"Item {code} not found")
    return item


def get_item_out(db: Session, code: str) -> ItemOut:
    """Fetch an item decorated with stock figures."""
    return _item_out(db, get_item(db, code))


def create_item(db: Session, payload: ItemIn) -> ItemOut:
    """Add an item to the master.

    The code is normalised (trimmed, upper case) and then fixed, because every
    other record in the system points at it. A duplicate is refused rather than
    quietly merged: two items sharing a code would silently pool their stock.
    """
    code = payload.code.strip().upper()
    if not code:
        raise DomainError("An item needs a code.")
    if repository.get_item(db, code) is not None:
        raise DuplicateError(f"Item {code} already exists")

    repository.add_item(
        db,
        Item(
            code=code,
            name=payload.name.strip(),
            category=payload.category,
            segment=payload.segment,
            uom=payload.uom.strip(),
            reorder_level=payload.reorder_level,
            is_active=payload.is_active,
        ),
    )
    db.commit()
    return get_item_out(db, code)


def update_item(db: Session, code: str, payload: ItemUpdate) -> ItemOut:
    """Correct an item's details. Only the fields supplied are touched.

    The code cannot be changed, so nothing that refers to this item is orphaned.
    Stock figures are untouched: they come from the ledger, not from here.
    """
    item = get_item(db, code)
    supplied = payload.model_dump(exclude_unset=True)

    if supplied.get("name") is not None:
        item.name = supplied["name"].strip()
    if supplied.get("uom") is not None:
        item.uom = supplied["uom"].strip()
    if "reorder_level" in supplied:
        item.reorder_level = supplied["reorder_level"]
    if supplied.get("category") is not None:
        item.category = supplied["category"]
    if supplied.get("segment") is not None:
        item.segment = supplied["segment"]
    if supplied.get("is_active") is not None:
        item.is_active = supplied["is_active"]

    db.commit()
    return get_item_out(db, code)


def delete_item(db: Session, code: str) -> None:
    """Remove an item that nothing refers to.

    Refused once the item has been bought, sold, made or consumed: its code sits
    on posted transactions and ledger rows, and deleting it would leave those
    records pointing at nothing. Set it **inactive** instead — the stock and the
    history stay exactly as they are, and it disappears from the item pickers.
    """
    item = get_item(db, code)
    used = repository.history_count(db, code)
    if used:
        raise DomainError(
            f"{code} is used by {used} record(s) and cannot be deleted. Set it to "
            f"inactive instead: the history stays, and it stops appearing in the "
            f"item lists."
        )
    repository.delete_item(db, item)
    db.commit()


def list_components(db: Session, parent_code: str) -> list[BomComponentOut]:
    """Return the direct components of a parent item."""
    out: list[BomComponentOut] = []
    for edge in repository.components_of(db, parent_code):
        component = repository.get_item(db, edge.component_code)
        out.append(
            BomComponentOut(
                parent_code=edge.parent_code,
                component_code=edge.component_code,
                component_name=component.name if component else edge.component_code,
                qty_per_unit=edge.qty_per_unit,
                stage=edge.stage,
                uom=component.uom if component else "",
            )
        )
    return out


def explode_bom(db: Session, parent_code: str, qty: Decimal, level: int = 1) -> list[BomExplosionLine]:
    """Recursively flatten a BOM into leaf-level material requirements.

    A component that is itself a manufactured item (has its own BOM) is expanded
    further, scaling quantities down each level. Items without a BOM are treated
    as purchasable leaves, which is where the recursion stops.
    """
    lines: list[BomExplosionLine] = []
    for edge in repository.components_of(db, parent_code):
        component = repository.get_item(db, edge.component_code)
        if component is None:
            continue
        required = money(to_decimal(edge.qty_per_unit) * qty)
        has_children = bool(repository.components_of(db, edge.component_code))
        if has_children:
            for child_line in explode_bom(db, edge.component_code, required, level + 1):
                child_line.level = max(child_line.level, level + 1)
                lines.append(child_line)
        else:
            position = ledger_service.position(db, component.code)
            lines.append(
                BomExplosionLine(
                    item_code=component.code,
                    item_name=component.name,
                    category=component.category,
                    uom=component.uom,
                    qty_per_unit=edge.qty_per_unit,
                    qty_required=required,
                    avg_cost=position.avg_cost,
                    est_cost=money(required * position.avg_cost),
                    level=level,
                )
            )
    return lines


def explode(db: Session, parent_code: str, qty: Decimal) -> BomExplosionOut:
    """Explode a BOM and total the estimated material cost."""
    parent = get_item(db, parent_code)
    lines = explode_bom(db, parent_code, qty)
    total = money(sum((line.est_cost for line in lines), Decimal("0")))
    return BomExplosionOut(
        parent_code=parent.code,
        parent_name=parent.name,
        qty=qty,
        lines=lines,
        total_estimated_cost=total,
    )
