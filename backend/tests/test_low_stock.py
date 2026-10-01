"""The reorder level, and the low-stock list built from it.

The rule worth pinning down is the one that decides whether the report is useful or
ignored: a **blank** reorder level means "not watched", not "reorder at zero". If
blank meant zero, every item in the system would have appeared on the list the day
the field was introduced.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.modules.purchases import service as purchases
from app.modules.purchases.schemas import PurchaseLineIn, PurchaseRequest

ADMIN = "admin@rpci.demo"
AS_OF = "2026-10-31"
POSTING_DATE = date(2026, 10, 12)


def _headers(login) -> dict[str, str]:
    status, body = login(ADMIN)
    assert status == 200, body
    return {"Authorization": f"Bearer {body['access_token']}"}


def _item(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    payload = {
        "code": "ZTEST-1",
        "name": "Watched Reagent",
        "category": "Raw Material",
        "segment": "Manufacturing",
        "uom": "kg",
    }
    payload.update(overrides)
    response = client.post("/api/items", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _buy(db, item_code: str, qty: str, cost: str = "50") -> None:
    purchases.post(
        db,
        PurchaseRequest(
            supplier="Stock Supplier",
            purchase_date=POSTING_DATE,
            lines=[
                PurchaseLineIn(
                    item_code=item_code, qty=Decimal(qty), unit_cost=Decimal(cost)
                )
            ],
        ),
    )


def _low_stock(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.get(
        "/api/reports/low-stock", params={"as_of": AS_OF}, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_an_item_with_no_reorder_level_is_never_listed(client, db, login) -> None:
    """Blank means "not watched" — the distinction the whole report rests on."""
    headers = _headers(login)
    _item(client, headers)  # no reorder_level
    _buy(db, "ZTEST-1", "1")  # one unit, which is nearly none

    assert _low_stock(client, headers)["rows"] == []


def test_an_item_at_or_below_its_level_is_listed_with_what_it_would_take(
    client, db, login
) -> None:
    """The shortfall is the answer, and its cost is what makes it a decision."""
    headers = _headers(login)
    _item(client, headers, reorder_level="100")
    _buy(db, "ZTEST-1", "20", cost="50")

    body = _low_stock(client, headers)
    assert len(body["rows"]) == 1

    row = body["rows"][0]
    assert row["code"] == "ZTEST-1"
    assert Decimal(row["qty_on_hand"]) == Decimal("20")
    assert Decimal(row["reorder_level"]) == Decimal("100")
    # 100 wanted, 20 held.
    assert Decimal(row["shortfall"]) == Decimal("80")
    assert Decimal(row["avg_cost"]) == Decimal("50")
    # Topping back up would cost 80 x 50.
    assert Decimal(row["reorder_value"]) == Decimal("4000")
    assert Decimal(body["total_reorder_value"]) == Decimal("4000")


def test_an_item_exactly_at_its_level_is_listed(client, db, login) -> None:
    """ "At the reorder level" is the trigger, not "below it"."""
    headers = _headers(login)
    _item(client, headers, reorder_level="20")
    _buy(db, "ZTEST-1", "20")

    row = _low_stock(client, headers)["rows"][0]
    assert Decimal(row["shortfall"]) == 0


def test_enough_stock_takes_the_item_off_the_list(client, db, login) -> None:
    """The list goes quiet on its own once the goods arrive."""
    headers = _headers(login)
    _item(client, headers, reorder_level="100")
    _buy(db, "ZTEST-1", "150")

    assert _low_stock(client, headers)["rows"] == []


def test_a_lapsed_item_is_not_something_to_reorder(client, db, login) -> None:
    """A discontinued line would otherwise sit on the list for ever."""
    headers = _headers(login)
    _item(client, headers, reorder_level="100", is_active=False)

    assert _low_stock(client, headers)["rows"] == []


def test_the_biggest_gap_comes_first(client, db, login) -> None:
    """The item most likely to run out should not need hunting for."""
    headers = _headers(login)
    _item(client, headers, code="SMALL-GAP", reorder_level="10")
    _item(client, headers, code="BIG-GAP", reorder_level="500")

    codes = [row["code"] for row in _low_stock(client, headers)["rows"]]
    assert codes == ["BIG-GAP", "SMALL-GAP"]


def test_the_level_can_be_set_and_cleared_again(client, db, login) -> None:
    """Blank stays a real state: an item can be taken off the watch list."""
    headers = _headers(login)
    _item(client, headers, reorder_level="100")
    assert len(_low_stock(client, headers)["rows"]) == 1

    cleared = client.patch(
        "/api/items/ZTEST-1", json={"reorder_level": None}, headers=headers
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["reorder_level"] is None
    assert _low_stock(client, headers)["rows"] == []


def test_the_item_master_reports_the_level_back(client, db, login) -> None:
    """The list on Inventory & BOM shows it, so the two screens agree."""
    headers = _headers(login)
    _item(client, headers, reorder_level="12.5")

    listed = client.get("/api/items", headers=headers).json()
    mine = next(item for item in listed if item["code"] == "ZTEST-1")
    assert Decimal(mine["reorder_level"]) == Decimal("12.5")
