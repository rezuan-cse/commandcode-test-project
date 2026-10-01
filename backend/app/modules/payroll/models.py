"""Payroll models: employees, the runs that pay them, and the lines produced.

A run snapshots each employee's gross, its component split and its deductions, so
what was paid stays readable even if the salary structure is changed later. The
underlying expense, deduction and net-pay amounts are posted as one balanced
journal entry.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.mixins import ReversibleMixin

# The departments that decide which salary account is charged.
OFFICE = "office"
FACTORY = "factory"


class Employee(Base):
    """A member of staff paid through the payroll."""

    __tablename__ = "employees"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    department: Mapped[str] = mapped_column(String(40), default=OFFICE, nullable=False)
    joining_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    bank_account: Mapped[str | None] = mapped_column(String(80), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(40), nullable=True)
    gross_salary: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0"), nullable=False
    )
    # Set when someone leaves. The record is kept rather than removed: a payroll
    # run that already paid them names them, and the history has to stay readable.
    left_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class PayrollRun(ReversibleMixin, Base):
    """One payroll run for a period, with the entry it posted."""

    __tablename__ = "payroll_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    pay_date: Mapped[date] = mapped_column(Date, nullable=False)
    gross_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0"), nullable=False
    )
    deductions_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0"), nullable=False
    )
    net_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0"), nullable=False
    )
    journal_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("journal_entries.id"), nullable=True
    )
    posted_by: Mapped[str] = mapped_column(String(80), default="system", nullable=False)
    posted_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    lines: Mapped[list["PayrollLine"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", lazy="selectin"
    )


class PayrollLine(Base):
    """One employee's pay within a run, with its component and deduction split."""

    __tablename__ = "payroll_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_code: Mapped[str] = mapped_column(
        ForeignKey("employees.code"), nullable=False
    )
    employee_name: Mapped[str] = mapped_column(String(160), nullable=False)
    gross: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    deductions: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    net: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    # Component and deduction breakdowns, stored as JSON text.
    components: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    deductions_detail: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    run: Mapped[PayrollRun] = relationship(back_populates="lines")
