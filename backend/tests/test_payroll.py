"""Payroll: salary structure from settings, a balanced posting, and RBAC."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

import pytest

from app.core.enums import Role
from app.core.exceptions import DomainError
from app.modules.journal_entries import repository as journal_repo
from app.modules.payroll import service
from app.modules.payroll.schemas import (
    DepartmentOption,
    EmployeeIn,
    PayrollOptionsIn,
    PayrollRequest,
)
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


def test_a_resigned_employee_leaves_the_payroll_and_keeps_their_history(db) -> None:
    """Resigning is recorded, not deleted.

    Payroll stops including them, the runs that already paid them still name them,
    and marking them active again brings them back.
    """
    _seed_staff(db)
    first = service.post_run(db, _request())
    assert len(first.preview.lines) == 2

    resigned = EmployeeIn(
        code="EMP-001",
        name="Office Person",
        department="office",
        gross_salary=Decimal("30000"),
        is_active=False,
        left_on=date(2026, 9, 30),
    )
    service.update_employee(db, "EMP-001", resigned)

    preview = service.preview_run(db, _request())
    assert [line.employee_code for line in preview.lines] == ["EMP-002"]

    # The run that already paid them is untouched.
    detail = service.get_run(db, first.run.id)
    assert {line.employee_code for line in detail.lines} == {"EMP-001", "EMP-002"}

    # Re-employing them clears the leaving date rather than carrying it forward.
    service.update_employee(
        db, "EMP-001", resigned.model_copy(update={"is_active": True})
    )
    db.expire_all()
    restored = service.list_employees(db)[0]
    assert restored.is_active is True
    assert restored.left_on is None


def test_only_admin_accountant_and_owner_may_read_payroll(
    client: TestClient, auth_headers
) -> None:
    """Payroll is outside Store and Sales reach, enforced by the server."""
    for role, expected in [
        (Role.ADMIN, 200),
        (Role.ACCOUNTANT, 200),
        (Role.OWNER_VIEWER, 200),
        (Role.STORE_PRODUCTION, 403),
        (Role.SALES_STAFF, 403),
    ]:
        response = client.get("/api/payroll/employees", headers=auth_headers(role))
        assert response.status_code == expected, role.value


def test_the_owner_may_read_but_not_change_payroll(
    client: TestClient, auth_headers
) -> None:
    """The owner's payroll access is view only."""
    owner = auth_headers(Role.OWNER_VIEWER)
    assert client.get("/api/payroll/employees", headers=owner).status_code == 200
    assert client.get("/api/payroll/runs", headers=owner).status_code == 200

    created = client.post(
        "/api/payroll/employees",
        json={"code": "EMP-900", "name": "New Person", "department": "office", "gross_salary": "1000"},
        headers=owner,
    )
    assert created.status_code == 403


def test_department_and_designation_come_from_the_managed_options(db) -> None:
    """Values are matched case-insensitively and stored in canonical form."""
    settings_service.seed_defaults(db)
    db.commit()
    emp = service.create_employee(
        db,
        EmployeeIn(
            code="EMP-010",
            name="Case Test",
            department="office",
            designation="accounts officer",
            gross_salary=Decimal("10000"),
        ),
    )
    assert emp.department == "Office"
    assert emp.designation == "Accounts Officer"


def test_unknown_department_or_designation_is_refused(db) -> None:
    """The dropdowns are closed lists: unknown values are rejected."""
    settings_service.seed_defaults(db)
    db.commit()
    with pytest.raises(DomainError):
        service.create_employee(
            db,
            EmployeeIn(
                code="EMP-011", name="Nope", department="Mars", gross_salary=Decimal("1")
            ),
        )
    with pytest.raises(DomainError):
        service.create_employee(
            db,
            EmployeeIn(
                code="EMP-012",
                name="Nope",
                department="Office",
                designation="Astronaut",
                gross_salary=Decimal("1"),
            ),
        )


def test_payroll_charges_each_department_to_its_own_account(db) -> None:
    """A custom department posts its pay to its own salary account."""
    settings_service.seed_defaults(db)
    db.commit()
    service.set_options(
        db,
        PayrollOptionsIn(
            departments=[
                DepartmentOption(name="Office", salary_account="6010"),
                DepartmentOption(name="Lab", salary_account="5011"),
            ],
            designations=["Scientist"],
        ),
    )
    service.create_employee(
        db,
        EmployeeIn(
            code="EMP-020",
            name="Lab Tech",
            department="lab",
            designation="Scientist",
            gross_salary=Decimal("20000"),
        ),
    )
    preview = service.preview_run(db, _request())
    debits = {
        line.account_code: line.debit
        for line in preview.journal_lines
        if line.debit > 0
    }
    assert debits["5011"] == 20000
    assert preview.balanced is True


def test_removing_a_department_in_use_is_refused(db) -> None:
    """Options can be managed freely, but not from under active employees."""
    settings_service.seed_defaults(db)
    db.commit()
    service.create_employee(
        db,
        EmployeeIn(
            code="EMP-030",
            name="Factory Hand",
            department="factory",
            gross_salary=Decimal("15000"),
        ),
    )
    with pytest.raises(DomainError, match="Factory"):
        service.set_options(
            db,
            PayrollOptionsIn(
                departments=[DepartmentOption(name="Office", salary_account="6010")],
                designations=["Worker"],
            ),
        )


def test_accountant_may_manage_options_but_store_may_not(
    client: TestClient, auth_headers
) -> None:
    """Whoever can run payroll can manage the dropdowns; nobody else can."""
    payload = {
        "departments": [{"name": "Office", "salary_account": "6010"}],
        "designations": ["Clerk"],
    }
    for role, expected in [
        (Role.ADMIN, 200),
        (Role.ACCOUNTANT, 200),
        (Role.OWNER_VIEWER, 403),
        (Role.STORE_PRODUCTION, 403),
        (Role.SALES_STAFF, 403),
    ]:
        response = client.put(
            "/api/payroll/options", json=payload, headers=auth_headers(role)
        )
        assert response.status_code == expected, role.value
