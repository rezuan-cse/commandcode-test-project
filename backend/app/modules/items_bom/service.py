"""Business logic for items and BOM, including recursive multi-stage explosion."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.money import money, to_decimal
from app.modules.inventory_ledger import service as ledger_service
from app.modules.items_bom import repository
from app.modules.items_bom.models import Item
from app.modules.items_bom.schemas import (
    BomComponentOut,
    BomExplosionLine,
    BomExplosionOut,
    ItemOut,
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
