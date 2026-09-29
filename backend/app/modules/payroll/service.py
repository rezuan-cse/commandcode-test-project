"""Business logic for payroll.

The salary structure and the deductions are read from the settings table, so no
rate or component is hardcoded. A run computes each employee's gross, its
component split and its deductions, then posts one balanced entry: the salary
expense is debited, the deductions and the net pay are credited.
"""

from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.accounting import DEFAULT_BANK_ACCOUNT
from app.core.enums import JournalSource
from app.core.exceptions import DuplicateError, NotFoundError
from app.core.money import money, ZERO
from app.core.numbering import next_voucher
from app.modules.accounts import repository as accounts_repo
from app.modules.journal_entries import repository as journal_repo
from app.modules.journal_entries import service as journal_service
from app.modules.journal_entries.models import JournalEntry
from app.modules.journal_entries.schemas import JournalLineIn
from app.modules.payroll import repository
from app.modules.payroll.models import Employee, PayrollLine, PayrollRun
from app.modules.payroll.schemas import (
    EmployeeIn,
    PayrollDetailOut,
    PayrollLineOut,
    PayrollPostResult,
    PayrollPreview,
    PayrollRequest,
    PayrollRunOut,
)
from app.modules.production.schemas import JournalLinePreview
from app.modules.settings import service as settings_service

HUNDRED = Decimal("100")


def _account_name(db: Session, code: str) -> str:
    """Look up an account's display name, falling back to its code."""
    account = accounts_repo.get_account(db, code)
    return account.name_en if account else code


def _defs(db: Session, key: str) -> list[dict]:
    """Read a list of {name, pct, account} definitions from the settings table."""
    value = settings_service.get_json(db, key)
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict) and row.get("name")]
    return []


def _pct(row: dict) -> Decimal:
    """Read a percentage out of a definition, tolerating a missing value."""
    try:
        return Decimal(str(row.get("pct", 0)))
    except Exception:  # noqa: BLE001 - a malformed percentage is treated as zero
        return ZERO


def _compute_line(db: Session, employee: Employee) -> PayrollLineOut:
    """Split one employee's gross into its components and deductions."""
    gross = money(employee.gross_salary)

    components: dict[str, Decimal] = {}
    for row in _defs(db, "payroll.salary_components"):
        components[str(row["name"])] = money(gross * _pct(row) / HUNDRED)

    deductions: dict[str, Decimal] = {}
    configured = _defs(db, "payroll.deductions")
    if configured:
        for row in configured:
            deductions[str(row["name"])] = money(gross * _pct(row) / HUNDRED)
    else:
        statutory = settings_service.get_number(db, "payroll.statutory_deduction_pct")
        if statutory > 0:
            deductions["Statutory deduction"] = money(gross * statutory / HUNDRED)

    deducted = money(sum(deductions.values(), ZERO))
    return PayrollLineOut(
        employee_code=employee.code,
        employee_name=employee.name,
        gross=gross,
        deductions=deducted,
        net=money(gross - deducted),
        components=components,
        deductions_detail=deductions,
    )


def _deduction_account(db: Session, name: str) -> str:
    """The account a named deduction is credited to."""
    for row in _defs(db, "payroll.deductions"):
        if str(row["name"]) == name and row.get("account"):
            return str(row["account"])
    return settings_service.get_account(db, "tax.tds_account")


def _journal(
    db: Session,
    office_total: Decimal,
    factory_total: Decimal,
    deduction_totals: dict[str, Decimal],
    net_total: Decimal,
) -> list[JournalLinePreview]:
    """Build the balanced payroll entry from the run's totals."""
    entries: list[JournalLinePreview] = []

    for total, key, label in (
        (office_total, "payroll.office_salary_account", "Office salaries"),
        (factory_total, "payroll.factory_labour_account", "Factory labour"),
    ):
        total = money(total)
        if total <= 0:
            continue
        account = settings_service.get_account(db, key)
        entries.append(
            JournalLinePreview(
                account_code=account,
                account_name=_account_name(db, account),
                segment="Shared",
                debit=total,
                credit=ZERO,
                narration=label,
            )
        )

    for name, amount in deduction_totals.items():
        amount = money(amount)
        if amount <= 0:
            continue
        account = _deduction_account(db, name)
        entries.append(
            JournalLinePreview(
                account_code=account,
                account_name=_account_name(db, account),
                segment="Shared",
                debit=ZERO,
                credit=amount,
                narration=f"{name} deducted",
            )
        )

    net_total = money(net_total)
    if net_total > 0:
        entries.append(
            JournalLinePreview(
                account_code=DEFAULT_BANK_ACCOUNT,
                account_name=_account_name(db, DEFAULT_BANK_ACCOUNT),
                segment="Shared",
                debit=ZERO,
                credit=net_total,
                narration="Salaries paid",
            )
        )
    return entries


def _assemble(db: Session, payload: PayrollRequest) -> PayrollPreview:
    """Compute the run: per-employee pay and the entry it will post."""
    employees = repository.list_employees(db, active_only=True)

    lines: list[PayrollLineOut] = []
    office_total = ZERO
    factory_total = ZERO
    net_total = ZERO
    deduction_totals: dict[str, Decimal] = {}

    for employee in employees:
        line = _compute_line(db, employee)
        lines.append(line)
        if employee.department == "factory":
            factory_total += line.gross
        else:
            office_total += line.gross
        for name, amount in line.deductions_detail.items():
            deduction_totals[name] = deduction_totals.get(name, ZERO) + amount
        net_total += line.net

    journal = _journal(db, office_total, factory_total, deduction_totals, net_total)
    debits = money(sum((line.debit for line in journal), ZERO))
    credits = money(sum((line.credit for line in journal), ZERO))

    warnings = []
    if not employees:
        warnings.append("There are no active employees, so there is nothing to pay.")

    return PayrollPreview(
        period_start=payload.period_start,
        period_end=payload.period_end,
        pay_date=payload.pay_date,
        lines=lines,
        gross_total=money(office_total + factory_total),
        deductions_total=money(sum(deduction_totals.values(), ZERO)),
        net_total=money(net_total),
        journal_lines=journal,
        balanced=debits == credits,
        warnings=warnings,
    )


def preview_run(db: Session, payload: PayrollRequest) -> PayrollPreview:
    """Preview a payroll run without changing anything."""
    return _assemble(db, payload)


def _encode(values: dict[str, Decimal]) -> str:
    """Store a component breakdown as JSON text."""
    return json.dumps({name: str(amount) for name, amount in values.items()})


def _line_out(line: PayrollLine) -> PayrollLineOut:
    """Decode a stored payroll line back into its component breakdown."""
    return PayrollLineOut(
        employee_code=line.employee_code,
        employee_name=line.employee_name,
        gross=money(line.gross),
        deductions=money(line.deductions),
        net=money(line.net),
        components={k: money(v) for k, v in json.loads(line.components).items()},
        deductions_detail={
            k: money(v) for k, v in json.loads(line.deductions_detail).items()
        },
    )


def post_run(db: Session, payload: PayrollRequest) -> PayrollPostResult:
    """Post a payroll run atomically: one balanced entry for the whole run."""
    try:
        preview = _assemble(db, payload)
        run_no = next_voucher(
            db, PayrollRun, "run_no", "PAY", also=[(JournalEntry, "voucher_no")]
        )

        run = PayrollRun(
            run_no=run_no,
            period_start=payload.period_start,
            period_end=payload.period_end,
            pay_date=payload.pay_date,
            gross_total=preview.gross_total,
            deductions_total=preview.deductions_total,
            net_total=preview.net_total,
            posted_by=payload.posted_by,
        )
        for line in preview.lines:
            run.lines.append(
                PayrollLine(
                    employee_code=line.employee_code,
                    employee_name=line.employee_name,
                    gross=line.gross,
                    deductions=line.deductions,
                    net=line.net,
                    components=_encode(line.components),
                    deductions_detail=_encode(line.deductions_detail),
                )
            )
        repository.add_run(db, run)

        entry = journal_service.build_entry(
            voucher_no=run_no,
            entry_date=payload.pay_date,
            lines=[
                JournalLineIn(
                    account_code=line.account_code,
                    segment=line.segment,
                    debit=line.debit,
                    credit=line.credit,
                    narration=line.narration,
                )
                for line in preview.journal_lines
            ],
            source=JournalSource.PAYROLL,
            narration=f"Auto-posted from payroll run {run_no}",
            reference=run_no,
            posted_by=payload.posted_by,
        )
        journal_repo.add_entry(db, entry)
        run.journal_entry_id = entry.id

        db.commit()
        return PayrollPostResult(
            run=PayrollRunOut.model_validate(run),
            preview=preview,
            message=f"Posted {run_no}: gross {run.gross_total}, net {run.net_total}",
        )
    except Exception:
        db.rollback()
        raise


def list_runs(db: Session, limit: int = 100) -> list[PayrollRun]:
    """List posted payroll runs."""
    return repository.list_runs(db, limit=limit)


def get_run(db: Session, run_id: int) -> PayrollDetailOut:
    """Fetch one posted run with its lines, for payslips."""
    run = repository.get_run(db, run_id)
    if run is None:
        raise NotFoundError(f"Payroll run {run_id} not found")
    return PayrollDetailOut(
        **PayrollRunOut.model_validate(run).model_dump(),
        lines=[_line_out(line) for line in run.lines],
    )


def reverse(
    db: Session,
    run_id: int,
    *,
    reason: str,
    posted_by: str,
    bypass_approval: bool = False,
    requested_by: str | None = None,
) -> PayrollRun:
    """Undo a posted payroll run, mirroring its entry."""
    run = repository.get_run(db, run_id)
    if run is None:
        raise NotFoundError(f"Payroll run {run_id} not found")

    if not bypass_approval:
        from app.modules.approvals import service as approvals

        approvals.gate(
            db,
            source_type="payroll",
            source_id=run.id,
            action="reverse",
            amount=run.gross_total,
            reason=reason,
            requested_by=requested_by or posted_by,
        )

    try:
        journal_service.reverse_for_transaction(
            db, run, reason=reason, posted_by=posted_by, reversal_date=run.pay_date
        )
        db.commit()
        return run
    except Exception:
        db.rollback()
        raise


# --- Employees ------------------------------------------------------------


def list_employees(db: Session, *, active_only: bool = False) -> list[Employee]:
    """List employees."""
    return repository.list_employees(db, active_only=active_only)


def create_employee(db: Session, payload: EmployeeIn) -> Employee:
    """Add an employee. The code must be unique."""
    if repository.get_employee(db, payload.code) is not None:
        raise DuplicateError(f"Employee {payload.code} already exists")
    employee = Employee(**payload.model_dump())
    repository.add_employee(db, employee)
    db.commit()
    return employee


def update_employee(db: Session, code: str, payload: EmployeeIn) -> Employee:
    """Update an employee."""
    employee = repository.get_employee(db, code)
    if employee is None:
        raise NotFoundError(f"Employee {code} not found")
    for field, value in payload.model_dump(exclude={"code"}).items():
        setattr(employee, field, value)
    db.commit()
    return employee
