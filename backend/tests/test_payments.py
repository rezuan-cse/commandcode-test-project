"""Receipts and payments, over HTTP.

The behaviour this file pins down is the behaviour the client will rely on when
they ask "how much does this customer owe us?":

* a receipt against an invoice settles it, in full or in part;
* an invoice cannot be paid more than it is worth;
* money with no invoice to settle is held on account for the partner, and can be
  applied to an invoice later — which is what a deposit is;
* reversing a receipt puts the invoice back to unpaid;
* money posted to the ledger still balances.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.modules.journal_entries import repository as journal_repo
from app.modules.payments import service as payments
from app.modules.purchases import service as purchases
from app.modules.purchases.schemas import PurchaseLineIn, PurchaseRequest
from app.modules.reports import service as reports

ADMIN = "admin@rpci.demo"
OWNER = "owner@rpci.demo"
POSTING_DATE = date(2026, 10, 12)
MONEY_ACCOUNT = "1010"


def _headers(login, email: str = ADMIN) -> dict[str, str]:
    status, body = login(email)
    assert status == 200, body
    return {"Authorization": f"Bearer {body['access_token']}"}


def _party(client, headers, code: str, name: str, kind: str) -> dict:
    response = client.post(
        "/api/parties",
        json={"code": code, "name": name, "kind": kind},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _stock(db) -> None:
    """Buy trading stock so there is something to sell.

    Bought from a plain name rather than a supplier record: these tests are about
    what happens to money, and the goods only need to exist.
    """
    purchases.post(
        db,
        PurchaseRequest(
            supplier="Stock Supplier",
            purchase_date=POSTING_DATE,
            lines=[
                PurchaseLineIn(
                    item_code="TRD001", qty=Decimal("10"), unit_cost=Decimal("1000")
                )
            ],
        ),
    )


def _sale(client, db, headers, party_code: str, qty: str = "2", price: str = "1500") -> dict:
    _stock(db)
    response = client.post(
        "/api/sales",
        json={
            "customer": "placeholder",
            "party_code": party_code,
            "sale_date": POSTING_DATE.isoformat(),
            "lines": [{"item_code": "TRD001", "qty": qty, "sale_price": price}],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["order"]


def _purchase(db, party_code: str, cost: str = "1000") -> None:
    """Buy stock on credit from a supplier record, so there is an invoice to pay."""
    purchases.post(
        db,
        PurchaseRequest(
            supplier="placeholder",
            party_code=party_code,
            purchase_date=POSTING_DATE,
            lines=[
                PurchaseLineIn(
                    item_code="TRD001", qty=Decimal("10"), unit_cost=Decimal(cost)
                )
            ],
        ),
    )


def _receipt(party_code: str, amount: str, allocations: list[dict] | None = None) -> dict:
    body = {
        "direction": "Receipt",
        "party_code": party_code,
        "pay_date": POSTING_DATE.isoformat(),
        "amount": amount,
        "money_account": MONEY_ACCOUNT,
        "allocations": allocations or [],
    }
    return body


def _outstanding(client, headers) -> list[dict]:
    return client.get("/api/payments/outstanding", headers=headers).json()


# --- Settling an invoice ----------------------------------------------------


def test_a_receipt_settles_an_invoice(client, db, login) -> None:
    """The ordinary case: a customer pays a bill, and the bill is settled."""
    headers = _headers(login)
    _party(client, headers, "CUS-1", "Karim Enterprise", "Customer")
    sale = _sale(client, db, headers, "CUS-1")

    response = client.post(
        "/api/payments",
        json=_receipt(
            "CUS-1", "3000", [{"sale_order_id": sale["id"], "amount": "3000"}]
        ),
        headers=headers,
    )
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["voucher_no"].startswith("RCV-")
    assert body["allocated"] == "3000.0000"
    assert body["on_account"] == "0.0000"
    assert body["party_name"] == "Karim Enterprise"
    assert body["allocations"][0]["invoice_no"] == sale["order_no"]

    # The invoice has left the outstanding list entirely.
    assert [row for row in _outstanding(client, headers) if row["kind"] == "sale"] == []

    # And the entry moves the money and the receivable, nothing else.
    entry = journal_repo.get_entry(db, body["journal_entry_id"])
    lines = {
        line.account_code: (line.debit, line.credit) for line in entry.lines
    }
    assert lines[MONEY_ACCOUNT] == (Decimal("3000.0000"), Decimal("0.0000"))
    assert lines["1100"] == (Decimal("0.0000"), Decimal("3000.0000"))
    assert reports.trial_balance(db, POSTING_DATE).difference == 0


def test_a_partial_receipt_leaves_the_rest_outstanding(client, db, login) -> None:
    """Part payment is normal, and the remainder stays visibly owed."""
    headers = _headers(login)
    _party(client, headers, "CUS-1", "Karim Enterprise", "Customer")
    sale = _sale(client, db, headers, "CUS-1")

    client.post(
        "/api/payments",
        json=_receipt(
            "CUS-1", "1200", [{"sale_order_id": sale["id"], "amount": "1200"}]
        ),
        headers=headers,
    )

    row = next(row for row in _outstanding(client, headers) if row["kind"] == "sale")
    assert row["total"] == "3000.0000"
    assert row["paid"] == "1200.0000"
    assert row["outstanding"] == "1800.0000"


def test_two_receipts_can_settle_one_invoice(client, db, login) -> None:
    """The outstanding figure accounts for what has already been paid."""
    headers = _headers(login)
    _party(client, headers, "CUS-1", "Karim Enterprise", "Customer")
    sale = _sale(client, db, headers, "CUS-1")

    first = client.post(
        "/api/payments",
        json=_receipt(
            "CUS-1", "1000", [{"sale_order_id": sale["id"], "amount": "1000"}]
        ),
        headers=headers,
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/payments",
        json=_receipt(
            "CUS-1", "2000", [{"sale_order_id": sale["id"], "amount": "2000"}]
        ),
        headers=headers,
    )
    assert second.status_code == 201, second.text

    assert [row for row in _outstanding(client, headers) if row["kind"] == "sale"] == []


def test_an_invoice_cannot_be_paid_more_than_it_is_worth(client, db, login) -> None:
    """The refusal names the figure, so it is obvious what to change."""
    headers = _headers(login)
    _party(client, headers, "CUS-1", "Karim Enterprise", "Customer")
    sale = _sale(client, db, headers, "CUS-1")

    response = client.post(
        "/api/payments",
        json=_receipt(
            "CUS-1", "5000", [{"sale_order_id": sale["id"], "amount": "5000"}]
        ),
        headers=headers,
    )
    assert response.status_code == 400, response.text
    assert "3,000.00 outstanding" in response.json()["detail"]


def test_a_receipt_cannot_exceed_its_own_allocations_budget(client, db, login) -> None:
    """Allocations must fit inside the money being handed over."""
    headers = _headers(login)
    _party(client, headers, "CUS-1", "Karim Enterprise", "Customer")
    _party(client, headers, "CUS-2", "Other Customer", "Customer")
    first = _sale(client, db, headers, "CUS-1", qty="2", price="1500")
    second = _sale(client, db, headers, "CUS-2", qty="2", price="1500")

    response = client.post(
        "/api/payments",
        json=_receipt(
            "CUS-1",
            "1000",
            [
                {"sale_order_id": first["id"], "amount": "1000"},
                {"sale_order_id": second["id"], "amount": "1000"},
            ],
        ),
        headers=headers,
    )
    assert response.status_code == 400, response.text
    # The second invoice belongs to somebody else, which is caught first.
    assert "different customer" in response.json()["detail"]


# --- Money on account -------------------------------------------------------


def test_money_with_no_invoice_is_held_on_account(client, db, login) -> None:
    """A deposit is money against a partner, not against a bill.

    This is the case that would otherwise need a manual journal, and would then be
    invisible when working out what the customer owes.
    """
    headers = _headers(login)
    _party(client, headers, "CUS-1", "Karim Enterprise", "Customer")
    sale = _sale(client, db, headers, "CUS-1")

    response = client.post(
        "/api/payments", json=_receipt("CUS-1", "5000"), headers=headers
    )
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["allocated"] == "0.0000"
    assert body["on_account"] == "5000.0000"
    assert body["allocations"] == []

    # The invoice is untouched: the deposit has not been claimed by anything yet.
    row = next(row for row in _outstanding(client, headers) if row["kind"] == "sale")
    assert row["invoice_no"] == sale["order_no"]
    assert row["outstanding"] == "3000.0000"


def test_on_account_money_can_be_applied_to_an_invoice_later(client, db, login) -> None:
    """The point of holding it on account: it is usable once the invoice exists."""
    headers = _headers(login)
    _party(client, headers, "CUS-1", "Karim Enterprise", "Customer")
    held = client.post(
        "/api/payments", json=_receipt("CUS-1", "5000"), headers=headers
    ).json()

    # The invoice arrives afterwards.
    sale = _sale(client, db, headers, "CUS-1")

    applied = client.post(
        f"/api/payments/{held['id']}/allocate",
        json={"allocations": [{"sale_order_id": sale["id"], "amount": "3000"}]},
        headers=headers,
    )
    assert applied.status_code == 200, applied.text

    body = applied.json()
    assert body["allocated"] == "3000.0000"
    assert body["on_account"] == "2000.0000"
    assert [row for row in _outstanding(client, headers) if row["kind"] == "sale"] == []


def test_allocating_more_than_is_held_is_refused(client, db, login) -> None:
    headers = _headers(login)
    _party(client, headers, "CUS-1", "Karim Enterprise", "Customer")
    held = client.post(
        "/api/payments", json=_receipt("CUS-1", "100"), headers=headers
    ).json()
    sale = _sale(client, db, headers, "CUS-1")

    response = client.post(
        f"/api/payments/{held['id']}/allocate",
        json={"allocations": [{"sale_order_id": sale["id"], "amount": "3000"}]},
        headers=headers,
    )
    assert response.status_code == 400, response.text
    assert "more than the" in response.json()["detail"]


# --- Paying a supplier ------------------------------------------------------


def test_a_payment_settles_a_purchase(client, db, login) -> None:
    """The mirror image: money out settles a payable."""
    headers = _headers(login)
    _party(client, headers, "SUP-1", "Resin Supplier", "Supplier")
    _purchase(db, "SUP-1")

    before = [row for row in _outstanding(client, headers) if row["kind"] == "purchase"]
    assert len(before) == 1
    assert before[0]["outstanding"] == "10000.0000"

    response = client.post(
        "/api/payments",
        json={
            "direction": "Payment",
            "party_code": "SUP-1",
            "pay_date": POSTING_DATE.isoformat(),
            "amount": "10000",
            "money_account": MONEY_ACCOUNT,
            "allocations": [
                {"purchase_order_id": before[0]["invoice_id"], "amount": "10000"}
            ],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["voucher_no"].startswith("PMT-")
    assert body["allocated"] == "10000.0000"

    entry = journal_repo.get_entry(db, body["journal_entry_id"])
    lines = {line.account_code: (line.debit, line.credit) for line in entry.lines}
    assert lines["2010"] == (Decimal("10000.0000"), Decimal("0.0000"))
    assert lines[MONEY_ACCOUNT] == (Decimal("0.0000"), Decimal("10000.0000"))

    assert [
        row for row in _outstanding(client, headers) if row["kind"] == "purchase"
    ] == []


# --- Reversal ---------------------------------------------------------------


def test_reversing_a_receipt_makes_the_invoice_unpaid_again(client, db, login) -> None:
    """A bounced cheque has to put the books back, without deleting anything."""
    headers = _headers(login)
    _party(client, headers, "CUS-1", "Karim Enterprise", "Customer")
    sale = _sale(client, db, headers, "CUS-1")
    receipt = client.post(
        "/api/payments",
        json=_receipt(
            "CUS-1", "3000", [{"sale_order_id": sale["id"], "amount": "3000"}]
        ),
        headers=headers,
    ).json()
    assert [row for row in _outstanding(client, headers) if row["kind"] == "sale"] == []

    reversed_ = client.post(
        f"/api/payments/{receipt['id']}/reverse",
        json={"reason": "Cheque returned unpaid"},
        headers=headers,
    )
    assert reversed_.status_code == 200, reversed_.text
    assert reversed_.json()["is_reversed"] is True

    # The invoice is outstanding again, and the money is back in the receivable.
    row = next(row for row in _outstanding(client, headers) if row["kind"] == "sale")
    assert row["outstanding"] == "3000.0000"

    # Nothing was deleted: the receipt and its allocation are still on record.
    kept = client.get(f"/api/payments/{receipt['id']}", headers=headers).json()
    assert kept["allocations"][0]["invoice_no"] == sale["order_no"]
    assert reports.trial_balance(db, POSTING_DATE).difference == 0


# --- Guards -----------------------------------------------------------------


def test_a_receipt_needs_an_invoice_linked_to_a_record(client, db, login) -> None:
    """Money cannot be attached to an invoice nobody owns.

    The refusal has to point at the fix, because the person hitting it is holding a
    real payment and needs to know what to do next.
    """
    headers = _headers(login)
    # A sale posted before the customer list existed: a name, no link.
    purchases.post(
        db,
        PurchaseRequest(
            supplier="Walk-in Supplier",
            purchase_date=POSTING_DATE,
            lines=[
                PurchaseLineIn(
                    item_code="TRD001", qty=Decimal("10"), unit_cost=Decimal("1000")
                )
            ],
        ),
    )
    from app.modules.sales import service as sales
    from app.modules.sales.schemas import SaleLineIn, SaleRequest

    order = sales.post(
        db,
        SaleRequest(
            customer="Walk-in Customer",
            sale_date=POSTING_DATE,
            lines=[
                SaleLineIn(item_code="TRD001", qty=Decimal("1"), sale_price=Decimal("100"))
            ],
        ),
    ).order
    _party(client, headers, "CUS-1", "Karim Enterprise", "Customer")

    response = client.post(
        "/api/payments",
        json=_receipt(
            "CUS-1", "100", [{"sale_order_id": order.id, "amount": "100"}]
        ),
        headers=headers,
    )
    assert response.status_code == 400, response.text
    assert "Adopt existing names" in response.json()["detail"]


def test_a_supplier_only_record_cannot_receive_money(client, db, login) -> None:
    headers = _headers(login)
    _party(client, headers, "SUP-1", "Resin Supplier", "Supplier")

    response = client.post(
        "/api/payments", json=_receipt("SUP-1", "100"), headers=headers
    )
    assert response.status_code == 400, response.text
    assert "supplier only" in response.json()["detail"]


def test_a_sale_cannot_be_settled_by_a_payment(client, db, login) -> None:
    """Direction and invoice type have to agree, or the ledger would be nonsense."""
    headers = _headers(login)
    _party(client, headers, "PAR-1", "Both Ways", "Customer and Supplier")
    sale = _sale(client, db, headers, "PAR-1")

    response = client.post(
        "/api/payments",
        json={
            "direction": "Payment",
            "party_code": "PAR-1",
            "pay_date": POSTING_DATE.isoformat(),
            "amount": "3000",
            "money_account": MONEY_ACCOUNT,
            "allocations": [{"sale_order_id": sale["id"], "amount": "3000"}],
        },
        headers=headers,
    )
    assert response.status_code == 400, response.text
    assert "receipt settles sales" in response.json()["detail"].lower()


def test_a_closed_period_refuses_a_payment(client, db, login) -> None:
    headers = _headers(login)
    _party(client, headers, "CUS-1", "Karim Enterprise", "Customer")
    client.patch(
        "/api/settings/posting.books_closed_through",
        json={"value": "2026-10-31"},
        headers=headers,
    )

    response = client.post(
        "/api/payments", json=_receipt("CUS-1", "100"), headers=headers
    )
    assert response.status_code == 400, response.text
    assert "closed through 2026-10-31" in response.json()["detail"]
    assert payments.list_payments(db) == []


def test_money_cannot_move_through_an_unlisted_account(client, db, login) -> None:
    headers = _headers(login)
    _party(client, headers, "CUS-1", "Karim Enterprise", "Customer")

    response = client.post(
        "/api/payments",
        json={**_receipt("CUS-1", "100"), "money_account": "9999"},
        headers=headers,
    )
    assert response.status_code == 400, response.text
    assert "Configuration" in response.json()["detail"]


def test_a_view_only_role_cannot_record_a_payment(client, db, login) -> None:
    """Cash handling is an accounting job; the Owner watches."""
    headers = _headers(login, OWNER)
    assert client.get("/api/payments", headers=headers).status_code == 200

    response = client.post(
        "/api/payments", json=_receipt("CUS-1", "100"), headers=headers
    )
    assert response.status_code == 403


def test_the_preview_shows_the_entry_before_it_is_posted(client, db, login) -> None:
    """Preview and post agree, and preview writes nothing."""
    headers = _headers(login)
    _party(client, headers, "CUS-1", "Karim Enterprise", "Customer")
    sale = _sale(client, db, headers, "CUS-1")

    response = client.post(
        "/api/payments/preview",
        json=_receipt(
            "CUS-1", "3000", [{"sale_order_id": sale["id"], "amount": "3000"}]
        ),
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["party_name"] == "Karim Enterprise"
    assert body["allocated"] == "3000.0000"
    assert body["on_account"] == "0.0000"
    accounts = {line["account_code"]: line for line in body["journal_lines"]}
    assert accounts[MONEY_ACCOUNT]["debit"] == "3000.0000"
    assert accounts["1100"]["credit"] == "3000.0000"

    # Nothing was written by a preview.
    assert payments.list_payments(db) == []
