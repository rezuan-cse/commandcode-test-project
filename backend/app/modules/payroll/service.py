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
from app.core.exceptions import DomainError, DuplicateError, NotFoundError
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
    DepartmentOption,
    EmployeeIn,
    PayrollDetailOut,
    PayrollLineOut,
    PayrollOptionsIn,
    PayrollOptionsOut,
    PayrollPostResult,
    PayrollPreview,
    PayrollRequest,
    PayrollRunOut,
)
from app.modules.settings.schemas import SettingUpdate
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
    dept_totals: dict[str, Decimal],
    departments: list[dict[str, str]],
    deduction_totals: dict[str, Decimal],
    net_total: Decimal,
) -> list[JournalLinePreview]:
    """Build the balanced payroll entry from the run's totals.

    One debit line per department that has pay in the run, charged to that
    department's salary account.
    """
    entries: list[JournalLinePreview] = []
    accounts = {dept["name"]: dept["salary_account"] for dept in departments}

    for name, total in dept_totals.items():
        total = money(total)
        if total <= 0:
            continue
        account = accounts[name]
        if accounts_repo.get_account(db, account) is None:
            raise DomainError(
                f"Salary account {account} for department '{name}' no longer "
                f"exists. Fix it in the department options."
            )
        entries.append(
            JournalLinePreview(
                account_code=account,
                account_name=_account_name(db, account),
                segment="Shared",
                debit=total,
                credit=ZERO,
                narration=f"{name} salaries",
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
    departments = get_departments(db)
    dept_by_key = {dept["name"].lower(): dept for dept in departments}
    dept_totals: dict[str, Decimal] = {dept["name"]: ZERO for dept in departments}

    lines: list[PayrollLineOut] = []
    net_total = ZERO
    deduction_totals: dict[str, Decimal] = {}
    warnings = []

    for employee in employees:
        line = _compute_line(db, employee)
        lines.append(line)
        dept = dept_by_key.get((employee.department or "").strip().lower())
        if dept is None:
            # The employee's department was removed after they were hired.
            # Their pay still has to post somewhere: charge the first
            # department and say so, rather than dropping it silently.
            dept = departments[0]
            warnings.append(
                f"{employee.name} is in removed department "
                f"'{employee.department}'; pay charged to {dept['name']}."
            )
        dept_totals[dept["name"]] = money(dept_totals[dept["name"]] + line.gross)
        for name, amount in line.deductions_detail.items():
            deduction_totals[name] = deduction_totals.get(name, ZERO) + amount
        net_total += line.net

    journal = _journal(db, dept_totals, departments, deduction_totals, net_total)
    debits = money(sum((line.debit for line in journal), ZERO))
    credits = money(sum((line.credit for line in journal), ZERO))

    if not employees:
        warnings.append("There are no active employees, so there is nothing to pay.")

    return PayrollPreview(
        period_start=payload.period_start,
        period_end=payload.period_end,
        pay_date=payload.pay_date,
        lines=lines,
        gross_total=money(sum(dept_totals.values(), ZERO)),
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


def post_run(
    db: Session, payload: PayrollRequest, *, posted_by: str = "system"
) -> PayrollPostResult:
    """Post a payroll run atomically: one balanced entry for the whole run.

    ``posted_by`` is the signed-in user, supplied by the router out of the
    session rather than trusted from the payload.
    """
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
            posted_by=posted_by,
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

        journal_service.assert_books_open(db, payload.pay_date)
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
            posted_by=posted_by,
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
    payload.department = _canonical_department(db, payload.department)
    payload.designation = _canonical_designation(db, payload.designation)
    employee = Employee(**_fields(payload))
    repository.add_employee(db, employee)
    db.commit()
    return employee


def update_employee(db: Session, code: str, payload: EmployeeIn) -> Employee:
    """Update an employee.

    Marking somebody inactive is how a resignation is recorded. They stay on the
    list and keep their history; payroll simply stops including them.
    """
    employee = repository.get_employee(db, code)
    if employee is None:
        raise NotFoundError(f"Employee {code} not found")
    payload.department = _canonical_department(db, payload.department)
    payload.designation = _canonical_designation(db, payload.designation)
    for field, value in _fields(payload, skip={"code"}).items():
        setattr(employee, field, value)
    db.commit()
    return employee


def _checked_departments(raw: object) -> list[dict[str, str]]:
    """Validate the departments setting shape: names with salary accounts."""
    if not isinstance(raw, list) or not raw:
        raise DomainError("payroll.departments must be a non-empty list.")
    seen: set[str] = set()
    checked: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise DomainError(
                "Each department must look like "
                '{"name": "Office", "salary_account": "6010"}.'
            )
        name = str(entry.get("name", "")).strip()
        account = str(entry.get("salary_account", "")).strip()
        if not name:
            raise DomainError("Every department needs a name.")
        if not account:
            raise DomainError(f"Department '{name}' needs a salary account.")
        if name.lower() in seen:
            raise DomainError(f"Duplicate department '{name}'.")
        seen.add(name.lower())
        checked.append({"name": name, "salary_account": account})
    return checked


def _checked_designations(raw: object) -> list[str]:
    """Validate the designations setting shape: a list of titles."""
    if not isinstance(raw, list) or not raw:
        raise DomainError("payroll.designations must be a non-empty list.")
    if not all(isinstance(item, str) and item.strip() for item in raw):
        raise DomainError("Every designation must be a non-empty title.")
    names = [item.strip() for item in raw]
    if len({name.lower() for name in names}) != len(names):
        raise DomainError("Duplicate designation.")
    return names


def get_departments(db: Session) -> list[dict[str, str]]:
    """Departments with the salary account each one's pay is charged to."""
    return _checked_departments(settings_service.get_json(db, "payroll.departments"))


def get_designations(db: Session) -> list[str]:
    """Job titles offered as the Designation dropdown."""
    return _checked_designations(settings_service.get_json(db, "payroll.designations"))


def get_options(db: Session) -> PayrollOptionsOut:
    """Both dropdown option lists for the employee form."""
    return PayrollOptionsOut(
        departments=[DepartmentOption(**dept) for dept in get_departments(db)],
        designations=get_designations(db),
    )


def set_options(db: Session, payload: PayrollOptionsIn) -> PayrollOptionsOut:
    """Replace both option lists.

    A department still used by active employees cannot be removed — move
    those people first. Salary accounts must exist.
    """
    departments = _checked_departments([dept.model_dump() for dept in payload.departments])
    for dept in departments:
        if accounts_repo.get_account(db, dept["salary_account"]) is None:
            raise DomainError(
                f"Unknown salary account {dept['salary_account']} "
                f"for department '{dept['name']}'."
            )
    designations = _checked_designations(payload.designations)
    removed = {dept["name"].lower() for dept in get_departments(db)} - {
        dept["name"].lower() for dept in departments
    }
    if removed:
        in_use = sorted(
            {
                employee.department
                for employee in repository.list_employees(db, active_only=True)
                if employee.department.lower() in removed
            }
        )
        if in_use:
            raise DomainError(
                "Cannot remove departments still used by active employees: "
                + ", ".join(in_use)
                + ". Move those employees first."
            )
    settings_service.update_setting(
        db, "payroll.departments", SettingUpdate(value=json.dumps(departments))
    )
    settings_service.update_setting(
        db, "payroll.designations", SettingUpdate(value=json.dumps(designations))
    )
    return get_options(db)


def _canonical_department(db: Session, value: str) -> str:
    """The configured department name matching ``value`` (case-insensitive)."""
    wanted = (value or "").strip().lower()
    departments = get_departments(db)
    for dept in departments:
        if dept["name"].lower() == wanted:
            return dept["name"]
    raise DomainError(
        f"Unknown department '{value}'. Choose one of: "
        + ", ".join(dept["name"] for dept in departments)
        + "."
    )


def _canonical_designation(db: Session, value: str | None) -> str | None:
    """The configured designation matching ``value`` (case-insensitive)."""
    if value is None or not value.strip():
        return None
    wanted = value.strip().lower()
    designations = get_designations(db)
    for name in designations:
        if name.lower() == wanted:
            return name
    raise DomainError(
        f"Unknown designation '{value}'. Choose one of: "
        + ", ".join(designations)
        + "."
    )


def _fields(payload: EmployeeIn, *, skip: set[str] | None = None) -> dict:
    """The stored values for an employee, with the leaving date kept consistent.

    Somebody active has no leaving date: it is cleared rather than left behind,
    so re-employing someone does not carry their old resignation with them.
    """
    data = payload.model_dump(exclude=skip or set())
    if data["is_active"]:
        data["left_on"] = None
    return data
