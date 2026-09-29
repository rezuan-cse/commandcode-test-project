"""Thin HTTP routes for VAT reporting."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.users_roles.service import require
from app.modules.vat_tax import service
from app.modules.vat_tax.schemas import VatSummary

router = APIRouter(prefix="/vat", tags=["vat"])

CAN_READ = Depends(require("reports", write=False))


@router.get("/summary", response_model=VatSummary, dependencies=[CAN_READ])
def vat_summary(
    date_from: dt.date,
    date_to: dt.date,
    db: Session = Depends(get_db),
) -> VatSummary:
    """Output VAT, input VAT and net payable over a period."""
    totals = service.summary(db, date_from, date_to)
    return VatSummary(date_from=date_from, date_to=date_to, **totals)
