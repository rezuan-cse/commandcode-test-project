"""Thin HTTP routes for demo housekeeping."""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.demo import service
from app.modules.demo.schemas import ResetResult

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/reset", response_model=ResetResult)
def reset_demo() -> ResetResult:
    """Wipe all posted data and re-seed from the client's workbook."""
    report = service.reset_demo()
    return ResetResult(
        seeded=report.seeded,
        counts=report.counts,
        message="Demo data restored to the original workbook state",
    )
