"""Payroll: salary structure from settings, a balanced posting, and RBAC."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.enums import Role
from app.modules.journal_entries import repository as journal_repo
from app.modules.payroll import service
from app.modules.payroll.schemas import EmployeeIn, PayrollRequest
from app.modules.reports import service as reports
from app.modules.settings import service as settings_service

PAY_DATE = date(2026, 10, 31)
PERIOD = (date(2026, 10, 1), date(2026, 10, 31))


def _request() -> PayrollRequest:
    return PayrollRequest(
        period_start=PERIOD[0], period_end=PERIOD[1], pay_date=PAY_DATE
    )


def _seed_staff(db) -> None:
    settings_service.seed_defaults(db)
    db.commit()
    service.create_employee(
        db,
        EmployeeIn(
            code="EMP-001",
            name="Office Person",
            department="office",
            gross_salary=Decimal("30000"),
        ),
    )
    service.create_employee(
        db,
        EmployeeIn(
            code="EMP-002",
            name="Factory Person",
            department="factory",
            gross_salary=Decimal("20000"),
        ),
    )


def test_a_run_splits_gross_and_deductions_from_settings(db) -> None:
    """Components and the statutory deduction come from the settings table."""
    _seed_staff(db)
    preview = service.preview_run(db, _request())

    office = next(line for line in preview.lines if line.employee_code == "EMP-001")
    # Basic 60% of 30,000.
    assert office.components["Basic"] == 18000
    assert office.components["House Rent"] == 9000
    # Statutory deduction defaults to 10%.
    assert office.deductions == 3000
    assert office.net == 27000

    assert preview.gross_total == 50000
    assert preview.deductions_total == 5000
    assert preview.net_total == 45000
    assert preview.balanced is True


def test_posting_a_run_balances_and_keeps_the_books_straight(db) -> None:
    """Office and factory go to different accounts, and the entry balances."""
    _seed_staff(db)
    result = service.post_run(db, _request())

    entry = journal_repo.get_entry(db, result.run.journal_entry_id)
    accounts = {line.account_code for line in entry.lines}
    assert "6010" in accounts  # office salaries
    assert "5011" in accounts  # factory labour
    assert sum(line.debit for line in entry.lines) == sum(
        line.credit for line in entry.lines
    )
    assert reports.trial_balance(db, PAY_DATE).difference == 0
    assert entry.source.value == "Payroll"

    # The stored run carries its per-employee lines, for payslips.
    detail = service.get_run(db, result.run.id)
    assert len(detail.lines) == 2
    assert detail.lines[0].components["Basic"] == 18000


def test_reversing_a_run_unwinds_it(db) -> None:
    """A reversed run leaves the trial balance at zero."""
    _seed_staff(db)
    result = service.post_run(db, _request())
    service.reverse(db, result.run.id, reason="Paid twice", posted_by="tester")
    db.expire_all()
    assert reports.trial_balance(db, PAY_DATE).difference == 0


def test_an_empty_payroll_warns_rather_than_posting_nothing_quietly(db) -> None:
    """With no staff the preview says so."""
    settings_service.seed_defaults(db)
    preview = service.preview_run(db, _request())
    assert preview.lines == []
    assert any("no active employees" in w.lower() for w in preview.warnings)


def test_only_admin_and_accountant_may_read_payroll(
    client: TestClient, auth_headers
) -> None:
    """Payroll is outside every other role's reach, enforced by the server."""
    for role, expected in [
        (Role.ADMIN, 200),
        (Role.ACCOUNTANT, 200),
        (Role.STORE_PRODUCTION, 403),
        (Role.SALES_STAFF, 403),
        (Role.OWNER_VIEWER, 403),
    ]:
        response = client.get("/api/payroll/employees", headers=auth_headers(role))
        assert response.status_code == expected, role.value
