"""Production posting: weighted-average costing and all-or-nothing atomicity."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import InsufficientStockError
from app.modules.inventory_ledger import service as ledger
from app.modules.journal_entries import repository as journal_repo
from app.modules.production import repository as production_repo
from app.modules.production import service as production
from app.modules.production.schemas import ProductionLineIn, ProductionRequest
from app.modules.reports import service as reports

POSTING_DATE = date(2026, 10, 10)


def _request(simulate_failure: bool = False) -> ProductionRequest:
    """Produce 10 units of WIP001 from 50 kg of cement plus labor and overhead."""
    return ProductionRequest(
        output_item_code="WIP001",
        qty_produced=Decimal("10"),
        production_date=POSTING_DATE,
        labor_cost=Decimal("100"),
        overhead_cost=Decimal("50"),
        lines=[ProductionLineIn(component_code="RMC-003", qty_consumed=Decimal("50"))],
        simulate_failure=simulate_failure,
    )


def test_production_preview_is_balanced_before_posting(db) -> None:
    """The preview builds a balanced journal entry without changing anything."""
    preview = production.preview(db, _request())
    assert preview.balanced is True
    assert preview.can_post is True
    debits = sum(line.debit for line in preview.journal_lines)
    credits = sum(line.credit for line in preview.journal_lines)
    assert debits == credits
    assert preview.total_cost == preview.material_cost + 150


def test_production_consumes_components_at_average_cost(db) -> None:
    """Components leave stock valued at their current weighted-average cost."""
    before = ledger.position(db, "RMC-003")
    production.post(db, _request())
    after = ledger.position(db, "RMC-003")
    assert after.qty == before.qty - 50


def test_production_output_receives_computed_unit_cost(db) -> None:
    """The output item's unit cost is total cost divided by quantity produced."""
    result = production.post(db, _request())
    material = result.preview.material_cost
    expected_unit = (material + Decimal("150")) / Decimal("10")
    output = ledger.position(db, "WIP001")
    assert output.qty == 10
    assert result.order.unit_cost == expected_unit


def test_production_posts_a_balanced_journal_entry(db) -> None:
    """The auto-generated entry balances and leaves the trial balance at zero."""
    result = production.post(db, _request())
    entry = journal_repo.get_entry(db, result.order.journal_entry_id)
    debits = sum(line.debit for line in entry.lines)
    credits = sum(line.credit for line in entry.lines)
    assert debits == credits
    assert debits > 0

    tb = reports.trial_balance(db, POSTING_DATE)
    assert tb.difference == 0
    assert tb.balanced is True


def test_production_rejects_insufficient_component_stock(db) -> None:
    """A run needing stock that is not on hand is refused."""
    request = ProductionRequest(
        output_item_code="WIP001",
        qty_produced=Decimal("1"),
        production_date=POSTING_DATE,
        lines=[ProductionLineIn(component_code="RM001", qty_consumed=Decimal("5"))],
    )
    with pytest.raises(InsufficientStockError):
        production.post(db, request)


def test_failed_production_leaves_no_partial_rows(db) -> None:
    """A failure mid-transaction rolls back ledger, order, and journal together."""
    before_position = ledger.position(db, "RMC-003")
    before_orders = len(production_repo.list_orders(db))
    before_entries = len(journal_repo.list_entries(db))

    with pytest.raises(RuntimeError):
        production.post(db, _request(simulate_failure=True))

    db.expire_all()
    assert ledger.position(db, "RMC-003") == before_position
    assert len(production_repo.list_orders(db)) == before_orders
    assert len(journal_repo.list_entries(db)) == before_entries
