"""The item master: adding, correcting, and what deletion refuses.

Items could previously only arrive from a workbook import, so the first time the
client launched a product there was no way to enter it. These cover the screen's
rules: a code is normalised and then fixed, only the fields supplied change, and
an item with any history cannot be deleted.

The endpoints are exercised over HTTP because the rules that matter are the ones
the API enforces, including who is allowed to write.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.modules.purchases import service as purchases
from app.modules.purchases.schemas import PurchaseLineIn, PurchaseRequest

ADMIN = "admin@rpci.demo"
SALES = "sales@rpci.demo"
POSTING_DATE = date(2026, 10, 12)


def _headers(login, email: str = ADMIN) -> dict[str, str]:
    status, body = login(email)
    assert status == 200, body
    return {"Authorization": f"Bearer {body['access_token']}"}


def _new_item(**overrides) -> dict:
    """A payload for an item that the sample data does not already contain."""
    payload = {
        "code": "ZTEST-1",
        "name": "Test Resin Powder",
        "category": "Raw Material",
        "segment": "Manufacturing",
        "uom": "kg",
    }
    payload.update(overrides)
    return payload


def test_an_item_is_added_with_a_normalised_code(client, login) -> None:
    """Case and stray spaces are tidied, so one item cannot be entered twice."""
    response = client.post(
        "/api/items", json=_new_item(code="  ztest-1 "), headers=_headers(login)
    )
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["code"] == "ZTEST-1"
    assert body["name"] == "Test Resin Powder"
    # A new item starts with no stock: the ledger is the only thing that puts
    # quantity and cost on an item. Compared as numbers, because an item with no
    # movements has no ledger row to carry a scale.
    assert Decimal(body["qty_on_hand"]) == 0
    assert Decimal(body["value_on_hand"]) == 0
    assert body["is_active"] is True


def test_a_duplicate_code_is_refused(client, login) -> None:
    """Two items sharing a code would silently pool their stock."""
    headers = _headers(login)
    client.post("/api/items", json=_new_item(), headers=headers)

    again = client.post(
        "/api/items", json=_new_item(name="Something else entirely"), headers=headers
    )
    assert again.status_code == 409, again.text
    assert "already exists" in again.json()["detail"]


def test_only_the_fields_supplied_are_changed(client, login) -> None:
    """A patch corrects what it names and leaves the rest alone."""
    headers = _headers(login)
    client.post("/api/items", json=_new_item(), headers=headers)

    response = client.patch(
        "/api/items/ZTEST-1",
        json={"name": "Renamed Resin", "category": "Packaging", "is_active": False},
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["name"] == "Renamed Resin"
    assert body["category"] == "Packaging"
    assert body["is_active"] is False
    assert body["uom"] == "kg"
    assert body["segment"] == "Manufacturing"


def test_an_unused_item_can_be_deleted(client, login) -> None:
    """A code typed by mistake, with nothing behind it, can simply go."""
    headers = _headers(login)
    client.post("/api/items", json=_new_item(code="TYPO-1"), headers=headers)

    removed = client.delete("/api/items/TYPO-1", headers=headers)
    assert removed.status_code == 200, removed.text

    assert client.get("/api/items/TYPO-1", headers=headers).status_code == 404


def test_an_item_with_history_cannot_be_deleted(client, db, login) -> None:
    """Once an item has been bought, deleting it would orphan the record.

    The refusal has to name the way out, because "no" on its own leaves the user
    stuck with an item they want gone.
    """
    headers = _headers(login)
    purchases.post(
        db,
        PurchaseRequest(
            supplier="Test Supplier",
            purchase_date=POSTING_DATE,
            lines=[
                PurchaseLineIn(
                    item_code="TRD001", qty=Decimal("5"), unit_cost=Decimal("100")
                )
            ],
        ),
    )

    response = client.delete("/api/items/TRD001", headers=headers)
    assert response.status_code == 400, response.text
    assert "inactive" in response.json()["detail"]

    # And the item is still there, with its stock intact.
    still_there = client.get("/api/items/TRD001", headers=headers)
    assert still_there.status_code == 200
    assert still_there.json()["qty_on_hand"] == "5.0000"


def test_a_view_only_role_cannot_add_an_item(client, login) -> None:
    """The master is guarded by the server, not by hiding the button.

    Sales Staff may read the item list — they need it to sell — but not change it.
    """
    headers = _headers(login, SALES)
    assert client.get("/api/items", headers=headers).status_code == 200

    response = client.post("/api/items", json=_new_item(code="NOPE-1"), headers=headers)
    assert response.status_code == 403
