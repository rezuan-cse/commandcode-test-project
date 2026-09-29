"""Thin HTTP routes for payroll."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.schemas import ReversalRequest
from app.modules.payroll import service
from app.modules.payroll.schemas import (
    EmployeeIn,
    EmployeeOut,
    PayrollDetailOut,
    PayrollPostResult,
    PayrollPreview,
    PayrollRequest,
    PayrollRunOut,
)
from app.modules.users_roles.service import Principal, require

router = APIRouter(prefix="/payroll", tags=["payroll"])

CAN_READ = Depends(require("payroll", write=False))
CAN_WRITE = Depends(require("payroll", write=True))


@router.get("/employees", response_model=list[EmployeeOut], dependencies=[CAN_READ])
def list_employees(db: Session = Depends(get_db)) -> list[EmployeeOut]:
    """List employees."""
    return service.list_employees(db)


@router.post(
    "/employees", response_model=EmployeeOut, status_code=201, dependencies=[CAN_WRITE]
)
def create_employee(
    payload: EmployeeIn, db: Session = Depends(get_db)
) -> EmployeeOut:
    """Add an employee."""
    return service.create_employee(db, payload)


@router.put(
    "/employees/{code}", response_model=EmployeeOut, dependencies=[CAN_WRITE]
)
def update_employee(
    code: str, payload: EmployeeIn, db: Session = Depends(get_db)
) -> EmployeeOut:
    """Update an employee."""
    return service.update_employee(db, code, payload)


@router.get("/runs", response_model=list[PayrollRunOut], dependencies=[CAN_READ])
def list_runs(db: Session = Depends(get_db)) -> list[PayrollRunOut]:
    """List posted payroll runs."""
    return service.list_runs(db)


@router.post(
    "/runs/preview", response_model=PayrollPreview, dependencies=[CAN_WRITE]
)
def preview_run(
    payload: PayrollRequest, db: Session = Depends(get_db)
) -> PayrollPreview:
    """Preview a payroll run and its journal entry."""
    return service.preview_run(db, payload)


@router.post(
    "/runs", response_model=PayrollPostResult, status_code=201, dependencies=[CAN_WRITE]
)
def post_run(
    payload: PayrollRequest, db: Session = Depends(get_db)
) -> PayrollPostResult:
    """Post a payroll run atomically."""
    return service.post_run(db, payload)


@router.get(
    "/runs/{run_id}", response_model=PayrollDetailOut, dependencies=[CAN_READ]
)
def get_run(run_id: int, db: Session = Depends(get_db)) -> PayrollDetailOut:
    """Fetch one run with its lines, for payslips."""
    return service.get_run(db, run_id)


@router.post("/runs/{run_id}/reverse", response_model=PayrollRunOut)
def reverse_run(
    run_id: int,
    payload: ReversalRequest,
    principal: Principal = Depends(require("payroll", write=True)),
    db: Session = Depends(get_db),
) -> PayrollRunOut:
    """Undo a posted payroll run."""
    return service.reverse(
        db,
        run_id,
        reason=payload.reason,
        posted_by=payload.posted_by,
        requested_by=principal.user.email,
    )
