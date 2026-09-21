"""Demo reset: a visitor's test data can be cleared without a redeploy."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.inventory_ledger import service as ledger
from app.modules.purchases import repository as purchases_repo
from app.modules.purchases import service as purchases
from app.modules.purchases.schemas import PurchaseLineIn, PurchaseRequest

PURCHASE_DATE = date(2026, 10, 15)
AS_OF = date(2026, 10, 31)


def _client() -> TestClient:
    return TestClient(app)


def test_reset_clears_posted_data(db) -> None:
    """After a reset, only the imported workbook data remains."""
    purchases.post(
        db,
        PurchaseRequest(
            supplier="Test Supplier",
            purchase_date=PURCHASE_DATE,
            lines=[PurchaseLineIn(item_code="TRD001", qty=Decimal("5"), unit_cost=Decimal("100"))],
        ),
    )
    assert len(purchases_repo.list_orders(db)) == 1
    assert ledger.position(db, "TRD001").qty == 5

    response = _client().post("/api/demo/reset")
    assert response.status_code == 200
    body = response.json()
    assert body["seeded"] is True
    assert body["counts"]["accounts"] == 89

    db.expire_all()
    assert len(purchases_repo.list_orders(db)) == 0
    assert ledger.position(db, "TRD001").qty == 0
    assert ledger.position(db, "RMC-003").qty == 790


def test_reset_restores_workbook_figures(db) -> None:
    """The reset leaves the books exactly as the workbook had them."""
    from app.modules.reports import service as reports

    _client().post("/api/demo/reset")
    db.expire_all()

    tb = reports.trial_balance(db, AS_OF)
    assert tb.difference == 0
    assert tb.total_debit == tb.total_credit

    bs = reports.balance_sheet(db, AS_OF)
    assert bs.total_assets == 801600
    assert bs.check == 0


def test_reset_is_refused_when_disabled(db, monkeypatch) -> None:
    """The endpoint can be switched off for a deployment that must not lose data."""
    monkeypatch.setattr(settings, "allow_demo_reset", False)
    response = _client().post("/api/demo/reset")
    assert response.status_code == 403
