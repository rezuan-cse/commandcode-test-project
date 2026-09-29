"""Data access for payroll."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.payroll.models import Employee, PayrollRun


def list_employees(db: Session, *, active_only: bool = False) -> list[Employee]:
    """List employees, optionally only the active ones."""
    stmt = select(Employee).order_by(Employee.code)
    if active_only:
        stmt = stmt.where(Employee.is_active.is_(True))
    return list(db.execute(stmt).scalars().all())


def get_employee(db: Session, code: str) -> Employee | None:
    """Fetch one employee by code."""
    return db.get(Employee, code)


def add_employee(db: Session, employee: Employee) -> Employee:
    """Persist a new employee."""
    db.add(employee)
    db.flush()
    return employee


def list_runs(db: Session, limit: int = 100) -> list[PayrollRun]:
    """List posted payroll runs, newest first."""
    stmt = select(PayrollRun).order_by(PayrollRun.id.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_run(db: Session, run_id: int) -> PayrollRun | None:
    """Fetch one run with its lines."""
    return db.get(PayrollRun, run_id)


def add_run(db: Session, run: PayrollRun) -> PayrollRun:
    """Persist a new run and its lines."""
    db.add(run)
    db.flush()
    return run
