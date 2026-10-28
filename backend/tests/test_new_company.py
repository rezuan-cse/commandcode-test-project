"""The path a brand-new company takes: no workbook, everything entered by hand.

Resinova has no previous books. This is the sequence it will follow — add an
account, record the capital introduced, and watch the reports and the setup
checklist come to life — exercised over HTTP, the same surface the browser uses.

The workbook import is a separate, still-supported path with its own tests.
"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.core.db import KEEP_ACCOUNTS, clear_all_data
from app.seed.starter import seed_starter

ADMIN = "admin@rpci.demo"


def _headers(login) -> dict[str, str]:
    status, body = login(ADMIN)
    assert status == 200, body
    return {"Authorization": f"Bearer {body['access_token']}"}


def _fresh(db) -> None:
    """An empty set of books with the starter chart, keeping the sign-in accounts."""
    from app.modules.settings import service as settings_service

    clear_all_data(db, keep=KEEP_ACCOUNTS)
    seed_starter(db)
    settings_service.seed_defaults(db)
    db.commit()


def _entry(
    client: TestClient,
    headers: dict,
    *,
    voucher: str,
    entry_date: str,
    debit: str,
    credit: str,
    amount: str,
    narration: str,
) -> dict:
    response = client.post(
        "/api/journal-entries",
        headers=headers,
        json={
            "voucher_no": voucher,
            "entry_date": entry_date,
            "narration": narration,
            "lines": [
                {"account_code": debit, "segment": "Shared", "debit": amount, "credit": "0"},
                {"account_code": credit, "segment": "Shared", "debit": "0", "credit": amount},
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- Adding an account -------------------------------------------------------


def test_an_account_can_be_added_over_http(db, client: TestClient, login) -> None:
    """The chart is no longer read-only, so a company can add its own bank account."""
    _fresh(db)
    headers = _headers(login)

    response = client.post(
        "/api/accounts",
        headers=headers,
        json={
            "code": "1999",
            "name_en": "Bank — Second Account",
            "account_type": "Asset",
            "segment": "Shared",
            "normal_balance": "Dr",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["code"] == "1999"


def test_a_duplicate_account_code_is_refused(db, client: TestClient, login) -> None:
    """Two accounts sharing a code would pool two balances into one line."""
    _fresh(db)
    headers = _headers(login)

    response = client.post(
        "/api/accounts",
        headers=headers,
        json={
            "code": "1010",
            "name_en": "A second cash account",
            "account_type": "Asset",
            "segment": "Shared",
            "normal_balance": "Dr",
        },
    )
    assert response.status_code == 409


def test_an_account_can_be_renamed(db, client: TestClient, login) -> None:
    _fresh(db)
    headers = _headers(login)

    response = client.patch(
        "/api/accounts/1020",
        headers=headers,
        json={"name_en": "Bank — City Bank Current"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["name_en"] == "Bank — City Bank Current"


# --- Opening capital ---------------------------------------------------------


def test_opening_capital_can_be_posted_and_the_books_still_balance(
    db, client: TestClient, login
) -> None:
    """The first entry a new company makes, and the one it could not make before.

    Dr Cash and Bank / Cr Share Capital. Without a screen for this, a company with
    no workbook had no way to record its own capital at all.
    """
    _fresh(db)
    headers = _headers(login)

    entry = _entry(
        client,
        headers,
        voucher="JV-0001",
        entry_date="2026-07-01",
        debit="1010",
        credit="3000",
        amount="500000",
        narration="Share capital introduced",
    )
    assert entry["source"] == "Manual"
    assert entry["posted_by"]

    balance = client.get(
        "/api/reports/balance-sheet?as_of=2026-11-30", headers=headers
    ).json()
    assert balance["total_assets"] == "500000.0000"
    assert balance["equity_per_gl"] == "500000.0000"
    assert balance["is_balanced"] is True

    trial = client.get("/api/reports/trial-balance?as_of=2026-11-30", headers=headers).json()
    assert trial["balanced"] is True
    assert trial["difference"] == "0.0000"


def test_an_unbalanced_entry_is_refused_over_http(db, client: TestClient, login) -> None:
    """The interface disables the button, but the server is the boundary."""
    _fresh(db)
    headers = _headers(login)

    response = client.post(
        "/api/journal-entries",
        headers=headers,
        json={
            "voucher_no": "JV-0002",
            "entry_date": "2026-07-01",
            "lines": [
                {"account_code": "1010", "segment": "Shared", "debit": "100", "credit": "0"},
                {"account_code": "3000", "segment": "Shared", "debit": "0", "credit": "99"},
            ],
        },
    )
    assert response.status_code == 422
    assert "unbalanced" in response.json()["detail"].lower()


# --- Fiscal year -------------------------------------------------------------


def test_the_balance_sheet_splits_on_the_fiscal_year_not_the_calendar_year(
    db, client: TestClient, login
) -> None:
    """Bangladesh runs July–June. Profit from July belongs to the current period.

    A calendar-year split put July–December profit into retained earnings and called
    the following January–June a new current period, so one trading year appeared
    as two.
    """
    _fresh(db)
    headers = _headers(login)

    # Prior year: 1,000 of income in May 2026 (before 1 July 2026).
    _entry(
        client,
        headers,
        voucher="JV-PRIOR",
        entry_date="2026-05-20",
        debit="1010",
        credit="4010",
        amount="1000",
        narration="Prior period income",
    )
    # Current year: 500 of income in August 2026 (after 1 July 2026).
    _entry(
        client,
        headers,
        voucher="JV-CURRENT",
        entry_date="2026-08-15",
        debit="1010",
        credit="4010",
        amount="500",
        narration="Current period income",
    )

    balance = client.get(
        "/api/reports/balance-sheet?as_of=2026-11-30", headers=headers
    ).json()

    assert balance["retained_earnings"] == "1000.0000"
    assert balance["current_period_profit"] == "500.0000"
    assert balance["is_balanced"] is True


def test_a_calendar_fiscal_year_is_honoured_when_configured(
    db, client: TestClient, login
) -> None:
    """The boundary is a setting, not a hardcoded July."""
    _fresh(db)
    headers = _headers(login)
    assert (
        client.patch(
            "/api/settings/company.fiscal_year_start_month",
            headers=headers,
            json={"value": "1"},
        ).status_code
        == 200
    )

    _entry(
        client,
        headers,
        voucher="JV-MAY",
        entry_date="2026-05-20",
        debit="1010",
        credit="4010",
        amount="1000",
        narration="Income in May",
    )

    balance = client.get(
        "/api/reports/balance-sheet?as_of=2026-11-30", headers=headers
    ).json()
    # With a January year, May is inside the current period.
    assert balance["retained_earnings"] == "0.0000"
    assert balance["current_period_profit"] == "1000.0000"


# --- The setup checklist -----------------------------------------------------


def _checklist(client: TestClient, headers: dict) -> dict[str, bool]:
    items = client.get("/api/setup/checklist", headers=headers).json()["items"]
    return {item["key"]: item["done"] for item in items}


def test_the_checklist_starts_mostly_unticked(db, client: TestClient, login) -> None:
    _fresh(db)
    headers = _headers(login)
    done = _checklist(client, headers)

    # The chart and the company's own details are already there; nothing the
    # company has to bring is.
    assert done["company"] is True
    assert done["vat"] is True
    assert done["items"] is False
    assert done["recipes"] is False
    assert done["parties"] is False
    assert done["opening"] is False
    assert done["first_sale"] is False


def test_the_checklist_ticks_as_the_company_sets_itself_up(
    db, client: TestClient, login
) -> None:
    """Each step is derived from the data, so there is nothing to keep in step."""
    _fresh(db)
    headers = _headers(login)

    _entry(
        client,
        headers,
        voucher="JV-CAPITAL",
        entry_date="2026-07-01",
        debit="1010",
        credit="3000",
        amount="100000",
        narration="Capital introduced",
    )
    assert _checklist(client, headers)["opening"] is True

    assert (
        client.post(
            "/api/items",
            headers=headers,
            json={
                "code": "RES-1",
                "name": "Resin A",
                "category": "Raw Material",
                "segment": "Manufacturing",
                "uom": "kg",
            },
        ).status_code
        == 201
    )
    assert _checklist(client, headers)["items"] is True

    assert (
        client.post(
            "/api/items/RES-1/bom",
            headers=headers,
            json={"component_code": "RES-1X", "qty_per_unit": "1"},
        ).status_code
        == 404
    )
    # A component has to exist first.
    client.post(
        "/api/items",
        headers=headers,
        json={
            "code": "RES-1X",
            "name": "Additive",
            "category": "Raw Material",
            "segment": "Manufacturing",
            "uom": "kg",
        },
    )
    assert (
        client.post(
            "/api/items/RES-1/bom",
            headers=headers,
            json={"component_code": "RES-1X", "qty_per_unit": "2"},
        ).status_code
        == 201
    )
    assert _checklist(client, headers)["recipes"] is True

    for code, kind in (("CUS-1", "Customer"), ("SUP-1", "Supplier")):
        assert (
            client.post(
                "/api/parties",
                headers=headers,
                json={"code": code, "name": f"Test {kind}", "kind": kind},
            ).status_code
            == 201
        )
    assert _checklist(client, headers)["parties"] is True

    # Not complete until a sale is posted, which is the point of the checklist.
    assert client.get("/api/setup/checklist", headers=headers).json()["complete"] is False


# --- The opening reporting period --------------------------------------------


def test_the_suggested_period_ends_today_when_there_is_no_history(
    db, client: TestClient
) -> None:
    """It used to be the sample workbook's dates, which a new company has not got."""
    _fresh(db)
    body = client.get("/api/meta").json()
    assert body["suggested_as_of"] == date.today().isoformat()


def test_the_suggested_period_ends_at_the_latest_posting(
    db, client: TestClient, login
) -> None:
    """A company that imported history should open on that history."""
    _fresh(db)
    headers = _headers(login)
    _entry(
        client,
        headers,
        voucher="JV-LATEST",
        entry_date="2026-09-09",
        debit="1010",
        credit="3000",
        amount="1",
        narration="Last posting",
    )

    body = client.get("/api/meta").json()
    assert body["suggested_as_of"] == "2026-09-09"
    # 9 September 2026 falls in the fiscal year that began 1 July 2026.
    assert body["suggested_from"] == "2026-07-01"


def test_the_suggested_period_respects_a_configured_fiscal_year(
    db, client: TestClient, login
) -> None:
    _fresh(db)
    headers = _headers(login)
    client.patch(
        "/api/settings/company.fiscal_year_start_month",
        headers=headers,
        json={"value": "1"},
    )
    _entry(
        client,
        headers,
        voucher="JV-SEP",
        entry_date="2026-09-09",
        debit="1010",
        credit="3000",
        amount="1",
        narration="September posting",
    )

    body = client.get("/api/meta").json()
    assert body["suggested_from"] == "2026-01-01"
