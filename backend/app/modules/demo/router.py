"""Thin HTTP routes for demo housekeeping."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.modules.demo import service
from app.modules.demo.schemas import ResetResult
from app.modules.users_roles.service import require_admin

router = APIRouter(prefix="/demo", tags=["demo"])

# Restoring the workbook state deletes every posted transaction, so it is
# restricted to an administrator rather than offered to anyone signed in.
ADMIN_ONLY = Depends(require_admin())


@router.post("/reset", response_model=ResetResult, dependencies=[ADMIN_ONLY])
def reset_demo() -> ResetResult:
    """Wipe all posted data and re-seed from the client's workbook."""
    report = service.reset_demo()
    return ResetResult(
        seeded=report.seeded,
        counts=report.counts,
        message="Demo data restored to the original workbook state",
    )
