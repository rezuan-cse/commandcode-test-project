"""Sales and purchase posting, including revenue/COGS and rollback behaviour."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import InsufficientStockError
from app.modules.inventory_ledger import service as ledger
from app.modules.journal_entries import repository as journal_repo
from app.modules.purchases import service as purchases
from app.modules.purchases.schemas import PurchaseLineIn, PurchaseRequest
from app.modules.reports import service as reports
from app.modules.sales import service as sales
from app.modules.sales.schemas import SaleLineIn, SaleRequest

POSTING_DATE = date(2026, 10, 12)


def _receive_stock(db, qty: str = "10", cost: str = "1000"):
    """Buy trading stock so there is something to sell."""
    return purchases.post(
        db,
        PurchaseRequest(
            supplier="Test Supplier",
            purchase_date=POSTING_DATE,
            lines=[
                PurchaseLineIn(item_code="TRD001", qty=Decimal(qty), unit_cost=Decimal(cost))
            ],
        ),
    )


def test_purchase_raises_stock_and_balances(db) -> None:
    """A purchase increases quantity, sets average cost, and balances."""
    before = ledger.position(db, "TRD001")
    result = _receive_stock(db)
    after = ledger.position(db, "TRD001")
    assert after.qty == before.qty + 10
    assert after.avg_cost == 1000

    entry = journal_repo.get_entry(db, result.order.journal_entry_id)
    assert sum(line.debit for line in entry.lines) == sum(line.credit for line in entry.lines)
    assert reports.trial_balance(db, POSTING_DATE).difference == 0


def test_sale_reduces_inventory_at_average_cost(db) -> None:
    """Stock leaves at the item's weighted-average cost."""
    _receive_stock(db)
    sales.post(
        db,
        SaleRequest(
            customer="Test Customer",
            sale_date=POSTING_DATE,
            lines=[SaleLineIn(item_code="TRD001", qty=Decimal("4"), sale_price=Decimal("1500"))],
        ),
    )
    position = ledger.position(db, "TRD001")
    assert position.qty == 6
    assert position.value == 6000


def test_sale_posts_revenue_and_cogs_in_one_entry(db) -> None:
    """Revenue and COGS land in a single balanced journal entry."""
    _receive_stock(db)
    result = sales.post(
        db,
        SaleRequest(
            customer="Test Customer",
            sale_date=POSTING_DATE,
            lines=[SaleLineIn(item_code="TRD001", qty=Decimal("4"), sale_price=Decimal("1500"))],
        ),
    )
    entry = journal_repo.get_entry(db, result.order.journal_entry_id)
    debits = sum(line.debit for line in entry.lines)
    credits = sum(line.credit for line in entry.lines)
    assert debits == credits
    assert result.order.revenue == 6000
    assert result.order.cogs == 4000
    assert result.preview.gross_profit == 2000


def test_sale_updates_segment_profit_and_loss(db) -> None:
    """The Trading segment picks up the sale's revenue and cost."""
    _receive_stock(db)
    sales.post(
        db,
        SaleRequest(
            customer="Test Customer",
            sale_date=POSTING_DATE,
            lines=[SaleLineIn(item_code="TRD001", qty=Decimal("4"), sale_price=Decimal("1500"))],
        ),
    )
    pnl = reports.pnl_by_segment(db, date(2026, 1, 1), POSTING_DATE)
    trading = next(row for row in pnl.segments if row.segment == "Trading")
    assert trading.revenue == 6000
    assert trading.cogs == 4000
    assert trading.gross_profit == 2000


def test_sale_rejects_overselling(db) -> None:
    """You cannot sell stock you do not have."""
    with pytest.raises(InsufficientStockError):
        sales.post(
            db,
            SaleRequest(
                customer="Test Customer",
                sale_date=POSTING_DATE,
                lines=[SaleLineIn(item_code="TRD001", qty=Decimal("5"), sale_price=Decimal("100"))],
            ),
        )


def test_failed_sale_leaves_no_partial_rows(db) -> None:
    """A failure mid-transaction rolls back stock and journal together."""
    _receive_stock(db)
    before_position = ledger.position(db, "TRD001")
    before_entries = len(journal_repo.list_entries(db))

    with pytest.raises(RuntimeError):
        sales.post(
            db,
            SaleRequest(
                customer="Test Customer",
                sale_date=POSTING_DATE,
                lines=[
                    SaleLineIn(item_code="TRD001", qty=Decimal("4"), sale_price=Decimal("1500"))
                ],
                simulate_failure=True,
            ),
        )

    db.expire_all()
    assert ledger.position(db, "TRD001") == before_position
    assert len(journal_repo.list_entries(db)) == before_entries
