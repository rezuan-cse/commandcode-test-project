"""Demo reset: a visitor's test data can be cleared without a redeploy."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.enums import Role
from app.modules.inventory_ledger import service as ledger
from app.modules.purchases import repository as purchases_repo
from app.modules.purchases import service as purchases
from app.modules.purchases.schemas import PurchaseLineIn, PurchaseRequest

PURCHASE_DATE = date(2026, 10, 15)
AS_OF = date(2026, 10, 31)


def _buy(db) -> None:
    """Post a purchase so there is something for the reset to remove."""
    purchases.post(
        db,
        PurchaseRequest(
            supplier="Test Supplier",
            purchase_date=PURCHASE_DATE,
            lines=[PurchaseLineIn(item_code="TRD001", qty=Decimal("5"), unit_cost=Decimal("100"))],
        ),
    )


def test_reset_clears_posted_data(client: TestClient, auth_headers, db) -> None:
    """After a reset, only the imported workbook data remains."""
    _buy(db)
    assert len(purchases_repo.list_orders(db)) == 1
    assert ledger.position(db, "TRD001").qty == 5

    response = client.post("/api/demo/reset", headers=auth_headers(Role.ADMIN))
    assert response.status_code == 200
    body = response.json()
    assert body["seeded"] is True
    assert body["counts"]["accounts"] == 89

    db.expire_all()
    assert len(purchases_repo.list_orders(db)) == 0
    assert ledger.position(db, "TRD001").qty == 0
    assert ledger.position(db, "RMC-003").qty == 790


def test_reset_restores_workbook_figures(client: TestClient, auth_headers, db) -> None:
    """The reset leaves the books exactly as the workbook had them."""
    from app.modules.reports import service as reports

    client.post("/api/demo/reset", headers=auth_headers(Role.ADMIN))
    db.expire_all()

    tb = reports.trial_balance(db, AS_OF)
    assert tb.difference == 0
    assert tb.total_debit == tb.total_credit

    bs = reports.balance_sheet(db, AS_OF)
    assert bs.total_assets == 801600
    assert bs.check == 0


def test_reset_is_refused_when_disabled(
    client: TestClient, auth_headers, monkeypatch
) -> None:
    """The endpoint can be switched off for a deployment that must not lose data."""
    monkeypatch.setattr(settings, "allow_demo_reset", False)
    response = client.post("/api/demo/reset", headers=auth_headers(Role.ADMIN))
    assert response.status_code == 403


def test_reset_requires_an_administrator(client: TestClient, auth_headers, db) -> None:
    """Wiping every posted transaction is not something any role may do."""
    _buy(db)

    for role in [Role.ACCOUNTANT, Role.STORE_PRODUCTION, Role.SALES_STAFF, Role.OWNER_VIEWER]:
        response = client.post("/api/demo/reset", headers=auth_headers(role))
        assert response.status_code == 403, role.value

    # The purchase is still there, so none of those attempts took effect.
    db.expire_all()
    assert len(purchases_repo.list_orders(db)) == 1


def test_reset_requires_a_session(client: TestClient, db) -> None:
    """Signed out means refused."""
    _buy(db)
    assert client.post("/api/demo/reset").status_code == 401

    db.expire_all()
    assert len(purchases_repo.list_orders(db)) == 1


@pytest.mark.parametrize("role", [Role.ADMIN])
def test_reset_is_allowed_for_admin(client: TestClient, auth_headers, role: Role) -> None:
    """The administrator can restore the demo."""
    assert client.post("/api/demo/reset", headers=auth_headers(role)).status_code == 200
