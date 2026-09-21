"""Business logic for production entry, including atomic auto-posting.

Posting a production run performs five things as one database transaction:
consumes components at their current weighted-average cost, sums the total cost,
computes the output unit cost, receipts the output at that cost, and writes a
balanced journal entry. Any failure rolls the whole thing back.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.accounting import DEFAULT_BANK_ACCOUNT, inventory_account
from app.core.enums import JournalSource, MovementType
from app.core.exceptions import InsufficientStockError, NotFoundError
from app.core.money import money, rate, to_decimal, ZERO
from app.core.numbering import next_voucher
from app.modules.accounts import repository as accounts_repo
from app.modules.inventory_ledger import service as ledger
from app.modules.items_bom import repository as items_repo
from app.modules.journal_entries import repository as journal_repo
from app.modules.journal_entries import service as journal_service
from app.modules.journal_entries.models import JournalEntry
from app.modules.journal_entries.schemas import JournalLineIn
from app.modules.production import repository
from app.modules.production.models import ProductionLine, ProductionOrder
from app.modules.production.schemas import (
    JournalLinePreview,
    ProductionLineIn,
    ProductionPreview,
    ProductionPostResult,
    ProductionRequest,
    ProductionRunOut,
    SuggestedComponent,
)


def _account_name(db: Session, code: str) -> str:
    """Look up an account's display name, falling back to its code."""
    account = accounts_repo.get_account(db, code)
    return account.name_en if account else code


def suggest_components(db: Session, output_item_code: str, qty: Decimal) -> list[SuggestedComponent]:
    """Scale the output item's BOM to ``qty`` and price each component."""
    suggestions: list[SuggestedComponent] = []
    for edge in items_repo.components_of(db, output_item_code):
        component = items_repo.get_item(db, edge.component_code)
        if component is None:
            continue
        required = money(to_decimal(edge.qty_per_unit) * qty)
        position = ledger.position(db, component.code)
        suggestions.append(
            SuggestedComponent(
                component_code=component.code,
                component_name=component.name,
                uom=component.uom,
                qty_per_unit=edge.qty_per_unit,
                qty_consumed=required,
                unit_cost=position.avg_cost,
                line_cost=money(required * position.avg_cost),
                on_hand=position.qty,
                sufficient=position.qty >= required,
            )
        )
    return suggestions


def _resolve_components(
    db: Session, payload: ProductionRequest
) -> list[SuggestedComponent]:
    """Use caller-supplied lines when given, otherwise fall back to the BOM."""
    suggestions = suggest_components(db, payload.output_item_code, payload.qty_produced)
    if not payload.lines:
        return suggestions

    by_code = {s.component_code: s for s in suggestions}
    resolved: list[SuggestedComponent] = []
    for line in payload.lines:
        base = by_code.get(line.component_code)
        component = items_repo.get_item(db, line.component_code)
        if component is None:
            raise NotFoundError(f"Component {line.component_code} not found")
        position = ledger.position(db, component.code)
        qty = money(line.qty_consumed)
        resolved.append(
            SuggestedComponent(
                component_code=component.code,
                component_name=component.name,
                uom=component.uom,
                qty_per_unit=base.qty_per_unit if base else ZERO,
                qty_consumed=qty,
                unit_cost=position.avg_cost,
                line_cost=money(qty * position.avg_cost),
                on_hand=position.qty,
                sufficient=position.qty >= qty,
            )
        )
    return resolved


def _journal_preview(
    db: Session,
    output_item_code: str,
    components: list[SuggestedComponent],
    total_cost: Decimal,
    labor: Decimal,
    overhead: Decimal,
    order_no: str,
) -> list[JournalLinePreview]:
    """Build the journal entry the posting will create, for on-screen preview."""
    output_item = items_repo.get_item(db, output_item_code)
    if output_item is None:
        raise NotFoundError(f"Item {output_item_code} not found")

    debit_account = inventory_account(output_item.category)
    lines = [
        JournalLinePreview(
            account_code=debit_account,
            account_name=_account_name(db, debit_account),
            segment=output_item.segment.value,
            debit=money(total_cost),
            credit=ZERO,
            narration=f"Production Order {order_no}: {output_item_code} output",
        )
    ]
    for component in components:
        item = items_repo.get_item(db, component.component_code)
        if item is None:
            continue
        credit_account = inventory_account(item.category)
        lines.append(
            JournalLinePreview(
                account_code=credit_account,
                account_name=_account_name(db, credit_account),
                segment=item.segment.value,
                debit=ZERO,
                credit=money(component.line_cost),
                narration=f"{component.component_code} consumed for {order_no}",
            )
        )
    conversion = money(to_decimal(labor) + to_decimal(overhead))
    if conversion > 0:
        lines.append(
            JournalLinePreview(
                account_code=DEFAULT_BANK_ACCOUNT,
                account_name=_account_name(db, DEFAULT_BANK_ACCOUNT),
                segment="Shared",
                debit=ZERO,
                credit=conversion,
                narration=f"Labor & OH paid for {order_no}",
            )
        )
    return lines


def _preview_from_parts(
    db: Session,
    payload: ProductionRequest,
    components: list[SuggestedComponent],
    order_no: str,
) -> ProductionPreview:
    """Assemble the cost build-up and journal preview from resolved components."""
    output_item = items_repo.get_item(db, payload.output_item_code)
    if output_item is None:
        raise NotFoundError(f"Item {payload.output_item_code} not found")

    material_cost = money(sum((c.line_cost for c in components), ZERO))
    labor = money(payload.labor_cost)
    overhead = money(payload.overhead_cost)
    total_cost = money(material_cost + labor + overhead)
    qty = money(payload.qty_produced)
    unit_cost = rate(total_cost / qty) if qty else ZERO

    journal_lines = _journal_preview(
        db, payload.output_item_code, components, total_cost, labor, overhead, order_no
    )
    debits = money(sum((line.debit for line in journal_lines), ZERO))
    credits = money(sum((line.credit for line in journal_lines), ZERO))

    warnings: list[str] = []
    short = [c.component_code for c in components if not c.sufficient]
    if short:
        warnings.append(f"Insufficient stock for: {', '.join(short)}")
    if not components:
        warnings.append("No components resolved for this production run")

    return ProductionPreview(
        output_item_code=output_item.code,
        output_item_name=output_item.name,
        qty_produced=qty,
        components=components,
        material_cost=material_cost,
        labor_cost=labor,
        overhead_cost=overhead,
        total_cost=total_cost,
        unit_cost=unit_cost,
        journal_lines=journal_lines,
        balanced=debits == credits,
        can_post=not short and bool(components),
        warnings=warnings,
    )


def preview(db: Session, payload: ProductionRequest) -> ProductionPreview:
    """Preview a production run without changing anything."""
    components = _resolve_components(db, payload)
    return _preview_from_parts(db, payload, components, "PROD-NEW")


def _assert_components_available(components: list[SuggestedComponent]) -> None:
    """Raise when any component is short, listing the offenders."""
    short = [f"{c.component_code} (need {c.qty_consumed}, have {c.on_hand})"
             for c in components if not c.sufficient]
    if short:
        raise InsufficientStockError("; ".join(short))


def _write_ledger_movements(
    db: Session,
    order: ProductionOrder,
    preview_data: ProductionPreview,
    journal_entry_id: int,
) -> None:
    """Consume each component, then receipt the output at the computed unit cost."""
    for component in preview_data.components:
        ledger.record_movement(
            db,
            item_code=component.component_code,
            movement_type=MovementType.PRODUCTION_OUT,
            movement_date=order.production_date,
            qty=component.qty_consumed,
            reference=order.order_no,
            journal_entry_id=journal_entry_id,
        )
    ledger.record_movement(
        db,
        item_code=order.output_item_code,
        movement_type=MovementType.PRODUCTION_IN,
        movement_date=order.production_date,
        qty=order.qty_produced,
        unit_cost=preview_data.unit_cost,
        reference=order.order_no,
        journal_entry_id=journal_entry_id,
    )


def post(db: Session, payload: ProductionRequest) -> ProductionPostResult:
    """Post a production run atomically.

    Either every ledger row and the journal entry commit together, or nothing
    does. ``simulate_failure`` exists purely to let the demo prove the rollback.
    """
    try:
        components = _resolve_components(db, payload)
        _assert_components_available(components)

        order_no = next_voucher(
            db,
            ProductionOrder,
            "order_no",
            "PROD",
            also=[(JournalEntry, "voucher_no")],
        )
        preview_data = _preview_from_parts(db, payload, components, order_no)

        order = ProductionOrder(
            order_no=order_no,
            production_date=payload.production_date,
            output_item_code=payload.output_item_code,
            qty_produced=money(payload.qty_produced),
            labor_cost=preview_data.labor_cost,
            overhead_cost=preview_data.overhead_cost,
            material_cost=preview_data.material_cost,
            total_cost=preview_data.total_cost,
            unit_cost=preview_data.unit_cost,
            posted_by=payload.posted_by,
        )
        for component in preview_data.components:
            order.lines.append(
                ProductionLine(
                    component_code=component.component_code,
                    qty_per_unit=component.qty_per_unit,
                    qty_consumed=component.qty_consumed,
                    unit_cost=component.unit_cost,
                    line_cost=component.line_cost,
                )
            )
        repository.add_order(db, order)

        entry = journal_service.build_entry(
            voucher_no=order_no,
            entry_date=payload.production_date,
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
            source=JournalSource.PRODUCTION,
            narration=f"Auto-posted from production order {order_no}",
            reference=order_no,
            posted_by=payload.posted_by,
        )
        journal_repo.add_entry(db, entry)
        order.journal_entry_id = entry.id

        _write_ledger_movements(db, order, preview_data, entry.id)

        if payload.simulate_failure:
            raise RuntimeError("Simulated failure injected to demonstrate rollback")

        db.commit()
        return ProductionPostResult(
            order=ProductionRunOut.model_validate(order),
            preview=preview_data,
            message=f"Posted {order_no}: balanced and committed",
        )
    except Exception:
        db.rollback()
        raise


def list_orders(db: Session, limit: int = 200) -> list[ProductionOrder]:
    """List posted production orders."""
    return repository.list_orders(db, limit=limit)
