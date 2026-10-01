"""Customer and supplier records, over HTTP.

The rules that matter here are the ones that make the list trustworthy as the
books grow: a name shown on a transaction is the record's own, a partner with
history is deactivated rather than deleted, and the names already sitting inside
old transactions can be adopted instead of retyped.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.modules.purchases import service as purchases
from app.modules.purchases.schemas import PurchaseLineIn, PurchaseRequest
from app.modules.sales import service as sales

ADMIN = "admin@rpci.demo"
OWNER = "owner@rpci.demo"
POSTING_DATE = date(2026, 10, 12)


def _headers(login, email: str = ADMIN) -> dict[str, str]:
    status, body = login(email)
    assert status == 200, body
    return {"Authorization": f"Bearer {body['access_token']}"}


def _receive_stock(db, supplier: str = "Test Supplier") -> None:
    """Buy trading stock from a named supplier, with no party record."""
    purchases.post(
        db,
        PurchaseRequest(
            supplier=supplier,
            purchase_date=POSTING_DATE,
            lines=[
                PurchaseLineIn(
                    item_code="TRD001", qty=Decimal("10"), unit_cost=Decimal("1000")
                )
            ],
        ),
    )


def _customer(code: str = "CUS-001", name: str = "Karim Enterprise") -> dict:
    return {"code": code, "name": name, "kind": "Customer"}


# --- Adding and correcting --------------------------------------------------


def test_a_record_is_added_with_a_normalised_code(client, login) -> None:
    """The code is tidied, so the same partner cannot be entered twice."""
    response = client.post(
        "/api/parties", json=_customer("  cus-001 "), headers=_headers(login)
    )
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["code"] == "CUS-001"
    assert body["name"] == "Karim Enterprise"
    assert body["kind"] == "Customer"
    # A blank form field arrives as null, not as an empty string.
    assert body["phone"] is None
    assert body["credit_days"] is None


def test_a_duplicate_code_is_refused(client, login) -> None:
    headers = _headers(login)
    client.post("/api/parties", json=_customer(), headers=headers)

    again = client.post(
        "/api/parties", json=_customer(name="Someone Else"), headers=headers
    )
    assert again.status_code == 409, again.text
    assert "already exists" in again.json()["detail"]


def test_only_the_fields_supplied_are_changed(client, login) -> None:
    """A patch corrects what it names and leaves the rest alone."""
    headers = _headers(login)
    client.post(
        "/api/parties",
        json={**_customer(), "phone": "01711-000000", "credit_days": 30},
        headers=headers,
    )

    response = client.patch(
        "/api/parties/CUS-001",
        json={"name": "Karim Enterprise Ltd", "credit_days": 45},
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["name"] == "Karim Enterprise Ltd"
    assert body["credit_days"] == 45
    assert body["phone"] == "01711-000000"
    assert body["kind"] == "Customer"


def test_the_customer_list_includes_partners_that_also_supply(client, login) -> None:
    """A firm marked "both" answers either question, so both lists show it."""
    headers = _headers(login)
    client.post(
        "/api/parties",
        json={"code": "PAR-1", "name": "Both Ways", "kind": "Customer and Supplier"},
        headers=headers,
    )
    client.post(
        "/api/parties",
        json={"code": "SUP-1", "name": "Supplier Only", "kind": "Supplier"},
        headers=headers,
    )

    customers = [p["name"] for p in client.get("/api/parties?kind=Customer", headers=headers).json()]
    suppliers = [p["name"] for p in client.get("/api/parties?kind=Supplier", headers=headers).json()]

    assert "Both Ways" in customers
    assert "Both Ways" in suppliers
    assert "Supplier Only" not in customers


# --- The link from a transaction -------------------------------------------


def test_a_sale_records_the_partys_name_not_the_forms(client, db, login) -> None:
    """The record wins, so the name shown and the identity cannot drift.

    The form here sends a misspelling, which is exactly the mistake the master
    list exists to prevent.
    """
    _receive_stock(db)
    headers = _headers(login)
    client.post("/api/parties", json=_customer(), headers=headers)

    response = client.post(
        "/api/sales",
        json={
            "customer": "Karim Enterpnse",
            "party_code": "CUS-001",
            "sale_date": POSTING_DATE.isoformat(),
            "lines": [{"item_code": "TRD001", "qty": "1", "sale_price": "1500"}],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text

    order = sales.list_orders(db)[0]
    assert order.party_code == "CUS-001"
    assert order.customer == "Karim Enterprise"


def test_an_unknown_party_code_is_refused(client, db, login) -> None:
    """A sale cannot point at a customer that does not exist."""
    _receive_stock(db)
    response = client.post(
        "/api/sales",
        json={
            "customer": "Nobody",
            "party_code": "CUS-999",
            "sale_date": POSTING_DATE.isoformat(),
            "lines": [{"item_code": "TRD001", "qty": "1", "sale_price": "1500"}],
        },
        headers=_headers(login),
    )
    assert response.status_code == 404


def test_adopting_existing_names_claims_their_history(client, db, login) -> None:
    """A supplier typed on an old purchase becomes a record that owns it.

    This is the migration path: the names are already in the system, so they are
    adopted rather than retyped from memory.
    """
    _receive_stock(db)
    headers = _headers(login)

    result = client.post("/api/parties/import-existing", headers=headers).json()
    assert result["created"] >= 1
    assert result["linked"] >= 1

    parties = client.get("/api/parties", headers=headers).json()
    adopted = next(p for p in parties if p["name"] == "Test Supplier")
    assert adopted["kind"] == "Supplier"
    assert adopted["code"].startswith("SUP-")

    order = purchases.list_orders(db)[0]
    assert order.party_code == adopted["code"]


def test_adopting_twice_changes_nothing_the_second_time(client, db, login) -> None:
    """The import is safe to press again, which is what makes it usable."""
    _receive_stock(db)
    headers = _headers(login)

    first = client.post("/api/parties/import-existing", headers=headers).json()
    second = client.post("/api/parties/import-existing", headers=headers).json()

    assert first["created"] >= 1
    assert second["created"] == 0
    assert second["already_known"] >= 1


# --- Removing ---------------------------------------------------------------


def test_an_unused_record_can_be_deleted(client, login) -> None:
    headers = _headers(login)
    client.post("/api/parties", json=_customer(code="TYPO-1"), headers=headers)

    assert client.delete("/api/parties/TYPO-1", headers=headers).status_code == 200
    assert client.get("/api/parties/TYPO-1", headers=headers).status_code == 404


def test_a_partner_named_on_a_transaction_cannot_be_deleted(client, db, login) -> None:
    """Deleting would leave the transaction's partner unresolved."""
    _receive_stock(db)
    headers = _headers(login)
    client.post("/api/parties", json=_customer(), headers=headers)
    client.post(
        "/api/sales",
        json={
            "customer": "Karim Enterprise",
            "party_code": "CUS-001",
            "sale_date": POSTING_DATE.isoformat(),
            "lines": [{"item_code": "TRD001", "qty": "1", "sale_price": "1500"}],
        },
        headers=headers,
    )

    response = client.delete("/api/parties/CUS-001", headers=headers)
    assert response.status_code == 400, response.text
    assert "inactive" in response.json()["detail"]
    assert client.get("/api/parties/CUS-001", headers=headers).status_code == 200


# --- Who may change it ------------------------------------------------------


def test_a_view_only_role_cannot_add_a_record(client, login) -> None:
    """The Owner sees the list; changing it is an administrator's or a trader's job."""
    headers = _headers(login, OWNER)
    assert client.get("/api/parties", headers=headers).status_code == 200

    response = client.post(
        "/api/parties", json=_customer(code="NOPE-1"), headers=headers
    )
    assert response.status_code == 403
