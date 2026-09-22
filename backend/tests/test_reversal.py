"""Reversing a posted transaction.

The important property is exactness: after a reversal, stock quantity, stock
value, average cost and the trial balance must all be where they were before the
original was posted. A reversal that is merely close would leave the stock sheet
and the accounts disagreeing — the very problem this system exists to remove.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.enums import MovementType, Role
from app.core.exceptions import DomainError, InsufficientStockError
from app.modules.inventory_ledger import service as ledger
from app.modules.production import repository as production_repo
from app.modules.production import service as production
from app.modules.production.schemas import ProductionLineIn, ProductionRequest
from app.modules.purchases import repository as purchases_repo
from app.modules.purchases import service as purchases
from app.modules.purchases.schemas import PurchaseLineIn, PurchaseRequest
from app.modules.reports import service as reports
from app.modules.sales import repository as sales_repo
from app.modules.sales import service as sales
from app.modules.sales.schemas import SaleLineIn, SaleRequest

POSTING_DATE = date(2026, 10, 15)
AS_OF = date(2026, 10, 31)

FILLER_COMPONENTS = [
    PurchaseLineIn(item_code="RMC-001", qty=Decimal("400"), unit_cost=Decimal("10")),
    PurchaseLineIn(item_code="RMC-002", qty=Decimal("100"), unit_cost=Decimal("20")),
    PurchaseLineIn(item_code="RMC-003", qty=Decimal("500"), unit_cost=Decimal("30")),
    PurchaseLineIn(item_code="RMC-004", qty=Decimal("150"), unit_cost=Decimal("10")),
    PurchaseLineIn(item_code="RMCD-005", qty=Decimal("100"), unit_cost=Decimal("50")),
    PurchaseLineIn(item_code="PKC-026", qty=Decimal("100"), unit_cost=Decimal("5")),
]


def _buy(db):
    """Stock the components needed to make TRD-018."""
    return purchases.post(
        db,
        PurchaseRequest(
            supplier="Rahman Traders",
            purchase_date=POSTING_DATE,
            lines=FILLER_COMPONENTS,
        ),
    )


def _produce(db, qty: str = "10"):
    """Make some TRD-018."""
    return production.post(
        db,
        ProductionRequest(
            output_item_code="TRD-018",
            qty_produced=Decimal(qty),
            production_date=POSTING_DATE,
            labor_cost=Decimal("500"),
            overhead_cost=Decimal("0"),
        ),
    )


def _sell(db, qty: str = "4", price: str = "600"):
    """Sell some TRD-018."""
    order = sales.post(
        db,
        SaleRequest(
            customer="Karim Enterprise",
            sale_date=POSTING_DATE,
            lines=[SaleLineIn(item_code="TRD-018", qty=Decimal(qty), sale_price=Decimal(price))],
        ),
    ).order
    db.expire_all()
    return order


def _position(db, code: str):
    """Quantity, value and average cost for an item."""
    return ledger.position(db, code)


# --- Sale ---------------------------------------------------------------


def test_reversing_a_sale_restores_exactly(db) -> None:
    """Stock, value and average cost return to precisely their prior figures."""
    _buy(db)
    _produce(db)
    before = _position(db, "TRD-018")
    order = _sell(db)

    sales.reverse(db, order.id, reason="wrong quantity", posted_by="sales")
    db.expire_all()
    after = _position(db, "TRD-018")

    assert after.qty == before.qty
    assert after.value == before.value
    assert after.avg_cost == before.avg_cost


def test_reversing_a_sale_unwinds_revenue_and_cogs(db) -> None:
    """The profit the sale created disappears with it."""
    _buy(db)
    _produce(db)
    before = reports.pnl_by_segment(db, POSTING_DATE, AS_OF)
    order = _sell(db)

    middle = reports.pnl_by_segment(db, POSTING_DATE, AS_OF)
    assert middle.total_revenue > before.total_revenue

    sales.reverse(db, order.id, reason="customer cancelled", posted_by="sales")
    db.expire_all()
    after = reports.pnl_by_segment(db, POSTING_DATE, AS_OF)

    assert after.total_revenue == before.total_revenue
    assert after.total_cogs == before.total_cogs
    assert after.net_profit == before.net_profit


def test_the_books_still_balance_after_a_sale_reversal(db) -> None:
    """The property the whole system rests on."""
    _buy(db)
    _produce(db)
    order = _sell(db)
    sales.reverse(db, order.id, reason="wrong item", posted_by="sales")
    db.expire_all()

    tb = reports.trial_balance(db, AS_OF)
    assert tb.balanced is True
    assert tb.difference == 0

    bs = reports.balance_sheet(db, AS_OF)
    assert bs.is_balanced is True
    assert bs.check == 0


def test_the_reversal_entry_mirrors_the_original(db) -> None:
    """Debits become credits, line for line."""
    from app.modules.journal_entries import repository as journal_repo

    _buy(db)
    _produce(db)
    order = _sell(db)
    original = journal_repo.get_entry(db, order.journal_entry_id)

    sales.reverse(db, order.id, reason="duplicate entry", posted_by="sales")
    db.expire_all()

    reversal = journal_repo.get_by_voucher(db, f"{order.order_no}-REV")
    assert reversal is not None
    assert len(reversal.lines) == len(original.lines)
    for before, after in zip(original.lines, reversal.lines):
        assert after.account_code == before.account_code
        assert after.debit == before.credit
        assert after.credit == before.debit


def test_the_sale_is_marked_reversed_and_not_removed(db) -> None:
    """The original stays on the record, which is the point of reversing."""
    _buy(db)
    _produce(db)
    order = _sell(db)

    sales.reverse(db, order.id, reason="wrong price", posted_by="sales")
    db.expire_all()

    kept = sales_repo.get_order(db, order.id)
    assert kept is not None
    assert kept.is_reversed is True
    assert kept.reversed_by == "sales"
    assert kept.reversal_reason == "wrong price"
    assert kept.reversal_journal_entry_id is not None
    # And it is still listed, so nothing has vanished.
    assert any(o.order_no == order.order_no for o in sales_repo.list_orders(db))


def test_a_sale_cannot_be_reversed_twice(db) -> None:
    """Otherwise stock would be put back more times than it was taken."""
    _buy(db)
    _produce(db)
    order = _sell(db)
    sales.reverse(db, order.id, reason="first", posted_by="sales")

    with pytest.raises(DomainError, match="already been reversed"):
        sales.reverse(db, order.id, reason="again", posted_by="sales")


# --- Purchase -----------------------------------------------------------


def test_reversing_a_purchase_restores_exactly(db) -> None:
    """The stock goes back out at the price paid, unwinding the average.

    The baseline is taken before the purchase, so this asserts the reversal
    returns the item to where it started — for RMC-003 that is the workbook's own
    figure of 790 kg at 32.27848101.
    """
    before = _position(db, "RMC-003")
    _buy(db)
    order = purchases_repo.list_orders(db)[0]

    purchases.reverse(db, order.id, reason="goods returned", posted_by="store")
    db.expire_all()
    after = _position(db, "RMC-003")

    assert after.qty == before.qty
    assert after.value == before.value
    assert after.avg_cost == before.avg_cost
    assert after.qty == 790
    assert str(after.avg_cost) == "32.27848101"


def test_reversing_a_purchase_is_refused_once_the_stock_is_used(db) -> None:
    """You cannot un-buy something you have already consumed.

    Refusing is the honest answer. Forcing it would drive the quantity negative
    and record a stock position that never existed.
    """
    _buy(db)
    _produce(db)  # consumes part of RMC-003
    order = purchases_repo.list_orders(db)[0]

    with pytest.raises(InsufficientStockError):
        purchases.reverse(db, order.id, reason="too late", posted_by="store")

    # And nothing was changed by the attempt.
    db.expire_all()
    assert purchases_repo.get_order(db, order.id).is_reversed is False
    assert reports.trial_balance(db, AS_OF).balanced is True


# --- Production ---------------------------------------------------------


def test_reversing_a_production_run_restores_components_and_output(db) -> None:
    """Output comes out, every component goes back in."""
    _buy(db)
    before_components = {code: _position(db, code) for code in
                         ["RMC-001", "RMC-002", "RMC-003", "RMC-004", "RMCD-005", "PKC-026"]}
    order = _produce(db).order
    db.expire_all()

    production.reverse(db, order.id, reason="wrong recipe", posted_by="store")
    db.expire_all()

    for code, position in before_components.items():
        assert _position(db, code) == position, code
    assert _position(db, "TRD-018").qty == 0


def test_reversing_production_is_refused_once_the_output_is_sold(db) -> None:
    """The finished goods are gone, so the run cannot be undone."""
    _buy(db)
    order = _produce(db).order
    _sell(db)

    with pytest.raises(InsufficientStockError):
        production.reverse(db, order.id, reason="too late", posted_by="store")

    db.expire_all()
    assert production_repo.get_order(db, order.id).is_reversed is False


def test_the_books_balance_after_a_production_reversal(db) -> None:
    """A full buy, make and reverse leaves the books sound."""
    _buy(db)
    order = _produce(db).order
    production.reverse(db, order.id, reason="mislabelled", posted_by="store")
    db.expire_all()

    tb = reports.trial_balance(db, AS_OF)
    assert tb.balanced is True
    assert tb.difference == 0
    assert reports.balance_sheet(db, AS_OF).is_balanced is True


# --- The ledger says what happened --------------------------------------


def test_the_ledger_shows_the_reversal_as_a_correction(db) -> None:
    """Rows are labelled so a reader can tell a correction from a fresh trade."""
    _buy(db)
    _produce(db)
    order = _sell(db)
    sales.reverse(db, order.id, reason="wrong quantity", posted_by="sales")
    db.expire_all()

    rows = ledger.list_rows(db, item_code="TRD-018")
    kinds = {row.movement_type for row in rows}
    assert MovementType.REVERSAL_IN in kinds
    correction = next(row for row in rows if row.movement_type == MovementType.REVERSAL_IN)
    assert correction.reference == f"{order.order_no}-REV"
    assert correction.journal_entry_id is not None


# --- Authorisation and validation ---------------------------------------


@pytest.fixture
def admin(client: TestClient) -> dict[str, str]:
    """Sign in as the administrator."""
    body = client.post(
        "/api/auth/login", json={"email": "admin@rpci.demo", "password": "rpci"}
    ).json()
    return {"Authorization": f"Bearer {body['access_token']}"}


def test_a_reversal_needs_a_reason(client: TestClient, auth_headers, db) -> None:
    """Reversing changes the accounts and the stock; a reason is required."""
    _buy(db)
    _produce(db)
    order = _sell(db)
    headers = auth_headers(Role.SALES_STAFF)

    missing = client.post(f"/api/sales/{order.id}/reverse", json={}, headers=headers)
    assert missing.status_code == 422

    too_short = client.post(
        f"/api/sales/{order.id}/reverse", json={"reason": "x"}, headers=headers
    )
    assert too_short.status_code == 422

    ok = client.post(
        f"/api/sales/{order.id}/reverse",
        json={"reason": "wrong quantity entered"},
        headers=headers,
    )
    assert ok.status_code == 200
    assert ok.json()["is_reversed"] is True


def test_a_role_without_write_access_cannot_reverse(
    client: TestClient, auth_headers, db
) -> None:
    """Reversing is a change to the books, so it needs write access."""
    _buy(db)
    _produce(db)
    order = _sell(db)

    for role in [Role.ACCOUNTANT, Role.STORE_PRODUCTION, Role.OWNER_VIEWER]:
        response = client.post(
            f"/api/sales/{order.id}/reverse",
            json={"reason": "attempted by the wrong role"},
            headers=auth_headers(role),
        )
        assert response.status_code == 403, role.value

    db.expire_all()
    assert sales_repo.get_order(db, order.id).is_reversed is False
