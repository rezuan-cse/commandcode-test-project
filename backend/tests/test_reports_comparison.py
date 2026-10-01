"""Period comparison.

The report exists so the owner can ask "how does this month compare with the last
one?" and get an answer without a spreadsheet. What is pinned down here is the
arithmetic of the movement — and the one case where there is no sensible answer,
a percentage change against a period that had nothing in it.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.modules.purchases import service as purchases
from app.modules.purchases.schemas import PurchaseLineIn, PurchaseRequest

ADMIN = "admin@rpci.demo"
JANUARY = "2026-01-15"
FEBRUARY = "2026-02-15"


def _headers(login) -> dict[str, str]:
    status, body = login(ADMIN)
    assert status == 200, body
    return {"Authorization": f"Bearer {body['access_token']}"}


def _stock(db) -> None:
    """Buy stock so there is something to sell."""
    purchases.post(
        db,
        PurchaseRequest(
            supplier="Stock Supplier",
            purchase_date=date(2026, 1, 5),
            lines=[
                PurchaseLineIn(
                    item_code="TRD001", qty=Decimal("20"), unit_cost=Decimal("500")
                )
            ],
        ),
    )


def _sell(client: TestClient, headers: dict[str, str], when: str, qty: str, price: str):
    response = client.post(
        "/api/sales",
        json={
            "customer": "Local Customer",
            "sale_date": when,
            "lines": [{"item_code": "TRD001", "qty": qty, "sale_price": price}],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text


def _compare(client: TestClient, headers: dict[str, str], **periods) -> dict:
    response = client.get("/api/reports/pnl-comparison", params=periods, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _line(body: dict, metric: str) -> dict:
    return next(line for line in body["total"]["lines"] if line["metric"] == metric)


def test_the_movement_between_two_months_is_reported(client, db, login) -> None:
    """The ordinary case: a month against the one before it."""
    headers = _headers(login)
    _stock(db)
    _sell(client, headers, JANUARY, qty="2", price="1000")  # 2,000
    _sell(client, headers, FEBRUARY, qty="3", price="1000")  # 3,000

    body = _compare(
        client,
        headers,
        period_1_from="2026-01-01",
        period_1_to="2026-01-31",
        period_2_from="2026-02-01",
        period_2_to="2026-02-28",
    )

    revenue = _line(body, "Revenue")
    assert Decimal(revenue["period_1"]) == Decimal("2000")
    assert Decimal(revenue["period_2"]) == Decimal("3000")
    assert Decimal(revenue["change"]) == Decimal("1000")
    # 2,000 -> 3,000 is a rise of half.
    assert Decimal(revenue["change_pct"]) == Decimal("50")


def test_a_fall_is_reported_as_a_negative_change(client, db, login) -> None:
    """A bad month has to look like one, and the percentage has to be negative."""
    headers = _headers(login)
    _stock(db)
    _sell(client, headers, JANUARY, qty="4", price="1000")  # 4,000
    _sell(client, headers, FEBRUARY, qty="2", price="1000")  # 2,000

    body = _compare(
        client,
        headers,
        period_1_from="2026-01-01",
        period_1_to="2026-01-31",
        period_2_from="2026-02-01",
        period_2_to="2026-02-28",
    )

    revenue = _line(body, "Revenue")
    assert Decimal(revenue["change"]) == Decimal("-2000")
    assert Decimal(revenue["change_pct"]) == Decimal("-50")


def test_a_change_against_nothing_has_no_percentage(client, db, login) -> None:
    """There is no percentage change from zero, so none is reported.

    Reporting one — 100%, or an enormous number — would be inventing a figure. The
    absolute movement is still given, which is the part that means something.
    """
    headers = _headers(login)
    _stock(db)
    _sell(client, headers, FEBRUARY, qty="3", price="1000")

    body = _compare(
        client,
        headers,
        period_1_from="2026-01-01",
        period_1_to="2026-01-31",
        period_2_from="2026-02-01",
        period_2_to="2026-02-28",
    )

    revenue = _line(body, "Revenue")
    assert Decimal(revenue["period_1"]) == 0
    assert Decimal(revenue["period_2"]) == Decimal("3000")
    assert Decimal(revenue["change"]) == Decimal("3000")
    assert revenue["change_pct"] is None


def test_a_margin_is_compared_in_points_not_percentages(client, db, login) -> None:
    """A margin is already a percentage; a percentage change of it would be nonsense."""
    headers = _headers(login)
    _stock(db)
    _sell(client, headers, JANUARY, qty="2", price="1000")
    _sell(client, headers, FEBRUARY, qty="2", price="1000")

    body = _compare(
        client,
        headers,
        period_1_from="2026-01-01",
        period_1_to="2026-01-31",
        period_2_from="2026-02-01",
        period_2_to="2026-02-28",
    )

    margin = _line(body, "Gross margin %")
    assert margin["is_percentage"] is True
    assert margin["change_pct"] is None


def test_every_segment_is_compared_including_the_total(client, db, login) -> None:
    """The tables line up, so a segment can be read straight across."""
    headers = _headers(login)
    _stock(db)
    _sell(client, headers, JANUARY, qty="1", price="1000")

    body = _compare(
        client,
        headers,
        period_1_from="2026-01-01",
        period_1_to="2026-01-31",
        period_2_from="2026-02-01",
        period_2_to="2026-02-28",
    )

    assert body["total"]["segment"] == "All segments"
    assert len(body["segments"]) > 1
    # Each segment carries the same four figures, so the rows line up.
    for segment in body["segments"]:
        assert [line["metric"] for line in segment["lines"]] == [
            "Revenue",
            "Cost of goods sold",
            "Gross profit",
            "Gross margin %",
        ]


def test_the_comparison_agrees_with_the_plain_pnl(client, db, login) -> None:
    """One piece of arithmetic behind both screens, so they cannot disagree."""
    headers = _headers(login)
    _stock(db)
    _sell(client, headers, JANUARY, qty="3", price="1200")

    body = _compare(
        client,
        headers,
        period_1_from="2026-01-01",
        period_1_to="2026-01-31",
        period_2_from="2026-02-01",
        period_2_to="2026-02-28",
    )
    plain = client.get(
        "/api/reports/pnl",
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    ).json()

    assert Decimal(_line(body, "Revenue")["period_1"]) == Decimal(str(plain["total_revenue"]))
    assert Decimal(_line(body, "Net profit")["period_1"]) == Decimal(str(plain["net_profit"]))


def test_a_period_that_ends_before_it_starts_is_refused(client, db, login) -> None:
    """A typo in the dates should say so, not return a table of zeros."""
    response = client.get(
        "/api/reports/pnl-comparison",
        params={
            "period_1_from": "2026-03-01",
            "period_1_to": "2026-02-01",
            "period_2_from": "2026-04-01",
            "period_2_to": "2026-04-30",
        },
        headers=_headers(login),
    )
    assert response.status_code == 400, response.text
    assert "before it starts" in response.json()["detail"]
