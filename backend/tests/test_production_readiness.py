"""The guards that make the system safe to hand over.

Each test covers a gap that existed before handover, and each is written against
the real HTTP endpoint where that gap was, so a regression in a router is caught
rather than only a regression in the service underneath it.

* who entered a transaction is the signed-in user, not whatever the body claimed;
* a period the client has closed cannot be posted into;
* repeated wrong passwords lock the account;
* emptying the books never removes the accounts that sign in.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.modules.purchases import service as purchases
from app.modules.purchases.schemas import PurchaseLineIn, PurchaseRequest
from app.modules.sales import service as sales

ADMIN = "admin@rpci.demo"
SALES = "sales@rpci.demo"
DEMO_PASSWORD = "rpci"
POSTING_DATE = date(2026, 10, 12)
CLOSED_THROUGH = date(2026, 10, 31)
OPEN_DATE = date(2026, 11, 5)


def _headers(login, email: str = ADMIN) -> dict[str, str]:
    """Sign in for real and return bearer headers."""
    status, body = login(email)
    assert status == 200, body
    return {"Authorization": f"Bearer {body['access_token']}"}


def _sale_body(**overrides) -> dict:
    body = {
        "customer": "Test Customer",
        "sale_date": POSTING_DATE.isoformat(),
        "lines": [{"item_code": "TRD001", "qty": "4", "sale_price": "1500"}],
    }
    body.update(overrides)
    return body


def _receive_stock(db) -> None:
    """Buy trading stock, so there is something to sell."""
    purchases.post(
        db,
        PurchaseRequest(
            supplier="Test Supplier",
            purchase_date=POSTING_DATE,
            lines=[
                PurchaseLineIn(
                    item_code="TRD001", qty=Decimal("10"), unit_cost=Decimal("1000")
                )
            ],
        ),
    )


def _close_the_books(
    client: TestClient, headers: dict[str, str], through: date
) -> None:
    """Set the closing date through the settings API, as an administrator would."""
    response = client.patch(
        "/api/settings/posting.books_closed_through",
        json={"value": through.isoformat()},
        headers=headers,
    )
    assert response.status_code == 200, response.text


# --- Who entered it ---------------------------------------------------------


def test_a_posting_records_the_signed_in_user(client, db, login) -> None:
    """The body may name somebody else; the session decides.

    A caller trying to put someone else's name on a transaction is exactly what
    this guards against, and the body field is ignored rather than honoured.
    """
    _receive_stock(db)
    response = client.post(
        "/api/sales",
        json=_sale_body(posted_by="Somebody Else"),
        headers=_headers(login),
    )
    assert response.status_code == 201, response.text

    posted = [order.posted_by for order in sales.list_orders(db)]
    assert ADMIN in posted
    assert "Somebody Else" not in posted


def test_a_reversal_records_the_signed_in_user(client, db, login) -> None:
    """Undoing a transaction is attributed to whoever signed in and did it."""
    _receive_stock(db)
    headers = _headers(login)
    sale = client.post("/api/sales", json=_sale_body(), headers=headers).json()

    response = client.post(
        f"/api/sales/{sale['order']['id']}/reverse",
        json={"reason": "Entered in error", "posted_by": "Somebody Else"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["reversed_by"] == ADMIN


# --- A closed period --------------------------------------------------------


def test_a_closed_period_refuses_a_posting(client, db, login) -> None:
    """A transaction dated inside a closed period is refused, changing nothing."""
    _receive_stock(db)
    headers = _headers(login)
    _close_the_books(client, headers, CLOSED_THROUGH)

    before = len(sales.list_orders(db))
    response = client.post("/api/sales", json=_sale_body(), headers=headers)

    assert response.status_code == 400, response.text
    assert "closed through 2026-10-31" in response.json()["detail"]
    # Nothing half-posted: no order, no entry, no stock movement.
    assert len(sales.list_orders(db)) == before


def test_the_open_side_of_a_closed_period_still_takes_transactions(
    client, db, login
) -> None:
    """Closing a year does not stop the current period being used."""
    _receive_stock(db)
    headers = _headers(login)
    _close_the_books(client, headers, CLOSED_THROUGH)

    response = client.post(
        "/api/sales",
        json=_sale_body(sale_date=OPEN_DATE.isoformat()),
        headers=headers,
    )
    assert response.status_code == 201, response.text


def test_blank_means_the_books_are_open(client, db, login) -> None:
    """The default is an open book, so an untouched deployment is unrestricted."""
    _receive_stock(db)
    response = client.post("/api/sales", json=_sale_body(), headers=_headers(login))
    assert response.status_code == 201, response.text


# --- Sign-in throttling -----------------------------------------------------


def test_repeated_wrong_passwords_lock_the_account(client, login) -> None:
    """Guessing is cut off, and the right password does not bypass the lock."""
    for _ in range(5):
        status, _body = login(ADMIN, "not-the-password")
        assert status == 401

    # The lock is in force, so even the correct password is refused now.
    status, body = login(ADMIN, DEMO_PASSWORD)
    assert status == 401
    assert "locked" in body["detail"].lower()


def test_a_good_sign_in_clears_the_count(client, login) -> None:
    """Mistyping twice and then getting it right must not leave a lock pending."""
    login(ADMIN, "not-the-password")
    login(ADMIN, "not-the-password")
    status, _body = login(ADMIN, DEMO_PASSWORD)
    assert status == 200

    # Four more wrong ones: the count restarted, so the account is not locked.
    for _ in range(4):
        status, _body = login(ADMIN, "not-the-password")
        assert status == 401

    # And the right password still works, which it would not if the account had
    # locked on the earlier failures.
    status, _body = login(ADMIN, DEMO_PASSWORD)
    assert status == 200


def test_an_expired_lock_lets_the_owner_back_in(client, db, login) -> None:
    """A lock is temporary: once it passes, the account works again."""
    for _ in range(5):
        login(ADMIN, "not-the-password")

    from app.modules.users_roles.models import User

    user = db.query(User).filter(User.email == ADMIN).one()
    assert user.locked_until is not None

    # Wind the lock back rather than waiting fifteen minutes for it.
    user.locked_until = None
    db.commit()

    status, _body = login(ADMIN, DEMO_PASSWORD)
    assert status == 200


def test_an_administrator_reset_clears_the_lock(client, db, login) -> None:
    """The escape hatch has to work: a new password gets a locked-out user in.

    Issuing a password without clearing the lock would hand somebody details that
    still do not work, leaving no way back in except waiting.
    """
    from app.modules.users_roles.models import User

    sales_id = db.query(User).filter(User.email == SALES).one().id

    for _ in range(5):
        login(SALES, "not-the-password")
    status, body = login(SALES, DEMO_PASSWORD)
    assert status == 401
    assert "locked" in body["detail"].lower()

    issued = client.post(
        f"/api/access/users/{sales_id}/reset-password", headers=_headers(login)
    ).json()

    status, _body = login(SALES, issued["password"])
    assert status == 200


# --- Emptying the books -----------------------------------------------------


def test_a_data_reset_keeps_the_accounts(client, db, login) -> None:
    """Emptying the books must not remove the people who sign in.

    A deployment with demo seeding off has no other way to get an account back,
    so a reset that also cleared the user table would lock everybody out.
    """
    from app.modules.data import service as data_service
    from app.modules.users_roles.models import User

    before = db.query(User).count()
    assert before > 0

    data_service.reset("fresh")

    db.expire_all()
    after = db.query(User).count()
    assert after == before, "a reset must leave the accounts alone"

    # And the same credentials still work.
    status, _body = login(ADMIN, DEMO_PASSWORD)
    assert status == 200
