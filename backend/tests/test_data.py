"""Fresh start and workbook import.

A new deployment starts from a built-in starter chart of accounts, and an
administrator can import a workbook or start over at any time.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.db import clear_all_data
from app.core.enums import Role
from app.modules.accounts.models import Account
from app.modules.data import service as data_service
from app.modules.reports import service as reports
from app.seed.starter import STARTER_ACCOUNTS, seed_starter

AS_OF = date(2026, 10, 31)


def _count(db, model) -> int:
    from sqlalchemy import func, select

    return db.execute(select(func.count()).select_from(model)).scalar_one()


def test_the_starter_chart_is_usable_and_balances(db) -> None:
    """A fresh start has accounts, no balances, and a trial balance at zero."""
    clear_all_data(db)
    added = seed_starter(db)
    db.commit()

    assert added == len(STARTER_ACCOUNTS)
    assert _count(db, Account) == len(STARTER_ACCOUNTS)
    assert reports.trial_balance(db, AS_OF).difference == 0


def test_the_starter_chart_is_idempotent(db) -> None:
    """Seeding twice does not duplicate accounts."""
    clear_all_data(db)
    seed_starter(db)
    seed_starter(db)
    db.commit()
    assert _count(db, Account) == len(STARTER_ACCOUNTS)


def test_reset_fresh_leaves_no_transactions(db) -> None:
    """Reset in fresh mode restores only the starter accounts."""
    report = data_service.reset("fresh")
    assert report.seeded is True
    assert report.counts["accounts"] == len(STARTER_ACCOUNTS)


def test_reset_none_leaves_the_books_empty(db) -> None:
    """Reset in none mode clears everything and adds nothing."""
    data_service.reset("none")
    db.expire_all()
    assert _count(db, Account) == 0


def test_import_replaces_the_books_from_a_workbook(db) -> None:
    """An import loads the workbook's figures."""
    content = Path(settings.seed_from_excel_path).read_bytes()
    report = data_service.import_bytes(content, replace=True)

    assert report.seeded is True
    assert report.counts["accounts"] == 89

    db.expire_all()
    assert reports.balance_sheet(db, AS_OF).total_assets == 801600


def test_import_endpoint_requires_an_administrator(
    client: TestClient, auth_headers
) -> None:
    """Only an administrator may replace the books."""
    content = Path(settings.seed_from_excel_path).read_bytes()
    files = {"file": ("workbook.xlsx", content, "application/vnd.ms-excel")}

    response = client.post(
        "/api/data/import", files=files, headers=auth_headers(Role.ACCOUNTANT)
    )
    assert response.status_code == 403

    ok = client.post(
        "/api/data/import", files=files, headers=auth_headers(Role.ADMIN)
    )
    assert ok.status_code == 200
    assert ok.json()["counts"]["accounts"] == 89
