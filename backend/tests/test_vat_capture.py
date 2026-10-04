"""Recording the VAT rate on a sale, and a customer's BIN.

Two small changes that the Mushak work depends on, and the reason each exists:

* a sale now keeps **the rate it was taxed at**, not just the amount. Mushak 9.1
  reports supplies grouped by rate slab, and without the rate there is no way to
  tell afterwards which sales were taxed at which slab once a rate has changed —
  so the test that matters most here is the one where the rate changes *after* a
  sale and the earlier sale still remembers its own.
* a customer can carry a **BIN**, optionally, because a tax invoice must show a
  business buyer's number while a walk-in retail customer has none.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.modules.purchases import service as purchases
from app.modules.purchases.schemas import PurchaseLineIn, PurchaseRequest

ADMIN = "admin@rpci.demo"
POSTING_DATE = date(2026, 10, 12)


def _headers(login) -> dict[str, str]:
    status, body = login(ADMIN)
    assert status == 200, body
    return {"Authorization": f"Bearer {body['access_token']}"}


def _stock(db) -> None:
    purchases.post(
        db,
        PurchaseRequest(
            supplier="Stock Supplier",
            purchase_date=POSTING_DATE,
            lines=[
                PurchaseLineIn(
                    item_code="TRD001", qty=Decimal("20"), unit_cost=Decimal("500")
                )
            ],
        ),
    )


def _set(client: TestClient, headers: dict[str, str], key: str, value: str) -> None:
    response = client.patch(
        f"/api/settings/{key}", json={"value": value}, headers=headers
    )
    assert response.status_code == 200, response.text


def _sell(client: TestClient, headers: dict[str, str], qty: str = "2") -> dict:
    """Sell 2 units at 1,000, and return the posted sale with its lines."""
    response = client.post(
        "/api/sales",
        json={
            "customer": "Local Customer",
            "sale_date": POSTING_DATE.isoformat(),
            "lines": [{"item_code": "TRD001", "qty": qty, "sale_price": "1000"}],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    sale = response.json()["order"]
    detail = client.get(f"/api/sales/{sale['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    return detail.json()


# --- The rate the sale was taxed at -----------------------------------------


def test_a_taxed_sale_records_the_rate_it_was_taxed_at(client, db, login) -> None:
    """15% on a 2,000 sale is 300 of tax, and the line says which rate made it."""
    headers = _headers(login)
    _stock(db)
    _set(client, headers, "vat.standard_rate_pct", "15")
    _set(client, headers, "vat.charge_vat", "true")

    line = _sell(client, headers)["lines"][0]
    assert Decimal(line["vat_rate_pct"]) == Decimal("15")
    assert Decimal(line["vat_amount"]) == Decimal("300")


def test_an_untaxed_sale_records_a_zero_rate(client, db, login) -> None:
    """Zero is a real answer, and different from "posted before we recorded rates"."""
    headers = _headers(login)
    _stock(db)

    line = _sell(client, headers)["lines"][0]
    assert Decimal(line["vat_rate_pct"]) == 0
    assert Decimal(line["vat_amount"]) == 0


def test_a_rate_change_does_not_rewrite_the_sales_already_posted(
    client, db, login
) -> None:
    """The whole reason the rate is stored.

    A return has to group a period's supplies by slab. If the rate moved in the
    middle of a period, the sales before the change must still report the rate they
    were actually taxed at — otherwise the return cannot be prepared from the books
    alone, and somebody has to remember what March's rate was.
    """
    headers = _headers(login)
    _stock(db)

    _set(client, headers, "vat.standard_rate_pct", "15")
    _set(client, headers, "vat.charge_vat", "true")
    earlier = _sell(client, headers)["lines"][0]

    _set(client, headers, "vat.standard_rate_pct", "7.5")
    later = _sell(client, headers)["lines"][0]

    assert Decimal(earlier["vat_rate_pct"]) == Decimal("15"), "the earlier sale moved"
    assert Decimal(earlier["vat_amount"]) == Decimal("300")
    assert Decimal(later["vat_rate_pct"]) == Decimal("7.5")
    assert Decimal(later["vat_amount"]) == Decimal("150")


# --- The buyer's BIN --------------------------------------------------------


def test_a_business_customer_can_carry_a_bin(client, login) -> None:
    headers = _headers(login)
    response = client.post(
        "/api/parties",
        json={
            "code": "CUS-BIN",
            "name": "Karim Enterprise",
            "kind": "Customer",
            "vat_reg_no": "002016027-0208",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["vat_reg_no"] == "002016027-0208"

    listed = client.get("/api/parties", headers=headers).json()
    mine = next(party for party in listed if party["code"] == "CUS-BIN")
    assert mine["vat_reg_no"] == "002016027-0208"


def test_a_retail_customer_needs_no_bin(client, login) -> None:
    """A walk-in has no registration number, and the invoice simply omits it."""
    headers = _headers(login)
    response = client.post(
        "/api/parties",
        json={"code": "WALK-IN", "name": "Walk-in Customer", "kind": "Customer"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["vat_reg_no"] is None


def test_a_bin_can_be_corrected_and_cleared(client, login) -> None:
    """A mistyped BIN has to be fixable, and blank is a real state again."""
    headers = _headers(login)
    client.post(
        "/api/parties",
        json={
            "code": "CUS-BIN",
            "name": "Karim Enterprise",
            "kind": "Customer",
            "vat_reg_no": "WRONG",
        },
        headers=headers,
    )

    fixed = client.patch(
        "/api/parties/CUS-BIN",
        json={"vat_reg_no": "002016027-0208"},
        headers=headers,
    )
    assert fixed.status_code == 200, fixed.text
    assert fixed.json()["vat_reg_no"] == "002016027-0208"

    cleared = client.patch(
        "/api/parties/CUS-BIN", json={"vat_reg_no": None}, headers=headers
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["vat_reg_no"] is None
