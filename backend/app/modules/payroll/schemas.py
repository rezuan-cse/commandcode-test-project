"""Pydantic schemas for payroll."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.clock import LocalDateTime
from app.core.schemas import ReversalOut
from app.modules.production.schemas import JournalLinePreview


class EmployeeIn(BaseModel):
    """Payload for creating or updating an employee."""

    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1)
    email: str | None = None
    designation: str | None = None
    department: str = Field(default="Office", min_length=1, max_length=40)
    joining_date: date | None = None
    bank_account: str | None = None
    mobile: str | None = None
    gross_salary: Decimal = Field(default=Decimal("0"), ge=0)
    left_on: date | None = None
    is_active: bool = True


class EmployeeOut(BaseModel):
    """An employee as shown on screen."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    email: str | None
    designation: str | None
    department: str
    joining_date: date | None
    bank_account: str | None
    mobile: str | None
    gross_salary: Decimal
    left_on: date | None = None
    is_active: bool


class DepartmentOption(BaseModel):
    """One department choice, with the account its salaries are charged to."""

    name: str = Field(min_length=1, max_length=40)
    salary_account: str = Field(min_length=1, max_length=20)


class PayrollOptionsIn(BaseModel):
    """Replacement option lists for the employee form's dropdowns."""

    departments: list[DepartmentOption] = Field(min_length=1)
    designations: list[str] = Field(min_length=1)


class PayrollOptionsOut(BaseModel):
    """The dropdown options for the employee form."""

    departments: list[DepartmentOption]
    designations: list[str]


class PayrollLineOut(BaseModel):
    """One employee's computed pay within a preview or a posted run."""

    employee_code: str
    employee_name: str
    gross: Decimal
    deductions: Decimal
    net: Decimal
    components: dict[str, Decimal]
    deductions_detail: dict[str, Decimal]


class PayrollRequest(BaseModel):
    """Payload for previewing or posting a payroll run."""

    period_start: date
    period_end: date
    pay_date: date


class PayrollPreview(BaseModel):
    """The computed pay and the journal entry a run will post."""

    period_start: date
    period_end: date
    pay_date: date
    lines: list[PayrollLineOut]
    gross_total: Decimal
    deductions_total: Decimal
    net_total: Decimal
    journal_lines: list[JournalLinePreview]
    balanced: bool
    warnings: list[str]


class PayrollRunOut(ReversalOut):
    """A posted payroll run."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    run_no: str
    period_start: date
    period_end: date
    pay_date: date
    gross_total: Decimal
    deductions_total: Decimal
    net_total: Decimal
    journal_entry_id: int | None
    posted_by: str
    posted_at: LocalDateTime | None = None


class PayrollDetailOut(PayrollRunOut):
    """A posted payroll run with its lines, for payslips."""

    lines: list[PayrollLineOut]


class PayrollPostResult(BaseModel):
    """Result of posting a payroll run."""

    run: PayrollRunOut
    preview: PayrollPreview
    message: str
