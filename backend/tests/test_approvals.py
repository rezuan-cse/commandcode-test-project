"""The configurable approval gate.

Off by default, a reversal happens at once. Switched on, it pauses: a request is
recorded and a *different* person with write access approves it, which then
carries the reversal out.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.exceptions import ApprovalRequiredError, PermissionDeniedError
from app.modules.approvals import service as approvals
from app.modules.purchases import service as purchases
from app.modules.purchases.schemas import PurchaseLineIn, PurchaseRequest
from app.modules.sales import service as sales
from app.modules.sales.schemas import SaleLineIn, SaleRequest
from app.modules.settings import service as settings_service
from app.modules.settings.schemas import SettingUpdate
from app.modules.users_roles.models import User

POSTING_DATE = date(2026, 10, 12)


def _enable(db) -> None:
    settings_service.seed_defaults(db)
    settings_service.update_setting(
        db, "posting.require_second_approval", SettingUpdate(value="true")
    )


def _user(db, email: str) -> User:
    return db.execute(select(User).where(User.email == email)).scalar_one()


def _posted_sale(db):
    purchases.post(
        db,
        PurchaseRequest(
            supplier="Test Supplier",
            purchase_date=POSTING_DATE,
            lines=[PurchaseLineIn(item_code="TRD001", qty=Decimal("10"), unit_cost=Decimal("1000"))],
        ),
    )
    return sales.post(
        db,
        SaleRequest(
            customer="Test Customer",
            sale_date=POSTING_DATE,
            lines=[SaleLineIn(item_code="TRD001", qty=Decimal("4"), sale_price=Decimal("1500"))],
        ),
    )


def test_reversal_is_immediate_when_the_gate_is_off(db) -> None:
    """The default: nothing changes about reversing."""
    result = _posted_sale(db)
    order = sales.reverse(db, result.order.id, reason="Mistake", posted_by="Sales")
    assert order.is_reversed is True


def test_the_gate_pauses_the_reversal_and_records_a_request(db) -> None:
    """Switched on, the reversal is held back rather than performed."""
    _enable(db)
    result = _posted_sale(db)

    with pytest.raises(ApprovalRequiredError):
        sales.reverse(
            db,
            result.order.id,
            reason="Mistake",
            posted_by="Sales",
            requested_by="sales@rpci.demo",
        )

    db.expire_all()
    order = sales.get_order(db, result.order.id)
    assert order.is_reversed is False
    pending = approvals.list_visible(db, _user(db, "admin@rpci.demo"))
    assert len(pending) == 1
    assert pending[0].status == "pending"


def test_a_second_person_approving_performs_the_reversal(db) -> None:
    """Approving executes the paused action as the approver."""
    _enable(db)
    result = _posted_sale(db)
    with pytest.raises(ApprovalRequiredError):
        sales.reverse(
            db,
            result.order.id,
            reason="Mistake",
            posted_by="Sales",
            requested_by="sales@rpci.demo",
        )

    request = approvals.list_visible(db, _user(db, "admin@rpci.demo"))[0]
    decided = approvals.approve(db, request.id, _user(db, "admin@rpci.demo"), note="ok")

    assert decided.status == "approved"
    db.expire_all()
    assert sales.get_order(db, result.order.id).is_reversed is True


def test_you_cannot_approve_your_own_request(db) -> None:
    """A second person is the whole point."""
    _enable(db)
    result = _posted_sale(db)
    with pytest.raises(ApprovalRequiredError):
        sales.reverse(
            db,
            result.order.id,
            reason="Mistake",
            posted_by="Admin",
            requested_by="admin@rpci.demo",
        )
    request = approvals.list_visible(db, _user(db, "admin@rpci.demo"))[0]
    with pytest.raises(PermissionDeniedError):
        approvals.approve(db, request.id, _user(db, "admin@rpci.demo"))


def test_rejecting_leaves_the_posting_alone(db) -> None:
    """A rejection simply means the action does not happen."""
    _enable(db)
    result = _posted_sale(db)
    with pytest.raises(ApprovalRequiredError):
        sales.reverse(
            db,
            result.order.id,
            reason="Mistake",
            posted_by="Sales",
            requested_by="sales@rpci.demo",
        )
    request = approvals.list_visible(db, _user(db, "admin@rpci.demo"))[0]
    approvals.reject(db, request.id, _user(db, "admin@rpci.demo"), note="not justified")

    db.expire_all()
    assert sales.get_order(db, result.order.id).is_reversed is False
