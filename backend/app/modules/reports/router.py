"""Thin HTTP routes for reports."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.reports import service
from app.modules.reports.schemas import (
    BalanceSheetOut,
    GeneralLedgerOut,
    IntegrityReport,
    PnlOut,
    TrialBalanceOut,
)
from app.modules.users_roles.service import require

router = APIRouter(prefix="/reports", tags=["reports"])

CAN_READ = Depends(require("reports", write=False))


@router.get("/general-ledger", response_model=GeneralLedgerOut, dependencies=[CAN_READ])
def general_ledger(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
) -> GeneralLedgerOut:
    """General ledger for a date range."""
    return service.general_ledger(db, date_from, date_to)


@router.get("/trial-balance", response_model=TrialBalanceOut, dependencies=[CAN_READ])
def trial_balance(
    as_of: date = Query(...), db: Session = Depends(get_db)
) -> TrialBalanceOut:
    """Trial balance as of a date."""
    return service.trial_balance(db, as_of)


@router.get("/pnl", response_model=PnlOut, dependencies=[CAN_READ])
def pnl(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
) -> PnlOut:
    """Profit and loss by segment."""
    return service.pnl_by_segment(db, date_from, date_to)


@router.get("/balance-sheet", response_model=BalanceSheetOut, dependencies=[CAN_READ])
def balance_sheet(
    as_of: date = Query(...), db: Session = Depends(get_db)
) -> BalanceSheetOut:
    """Balance sheet as of a date."""
    return service.balance_sheet(db, as_of)


@router.get("/integrity", response_model=IntegrityReport, dependencies=[CAN_READ])
def integrity(
    as_of: date = Query(...), db: Session = Depends(get_db)
) -> IntegrityReport:
    """Data-integrity assertions for the dashboard."""
    return service.integrity_report(db, as_of)
