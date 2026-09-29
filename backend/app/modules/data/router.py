"""Thin HTTP routes for importing a workbook and starting over."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.exceptions import DomainError
from app.modules.data import service
from app.modules.data.schemas import DataResult
from app.modules.users_roles.service import require_admin

router = APIRouter(prefix="/data", tags=["data"])

ADMIN_ONLY = Depends(require_admin())


@router.post("/import", response_model=DataResult, dependencies=[ADMIN_ONLY])
async def import_workbook(
    file: UploadFile = File(...),
    replace: bool = Form(True),
) -> DataResult:
    """Import an uploaded .xlsx workbook. Admin only.

    With ``replace`` on (the default) the books are emptied first, so an import
    is a fresh set of books rather than a merge.
    """
    content = await file.read()
    if not content:
        raise DomainError("The uploaded file is empty.")

    try:
        report = service.import_bytes(content, replace=replace)
    except (KeyError, ValueError) as exc:
        raise DomainError(
            f"Could not read the workbook: {exc}. A sheet may be missing or renamed."
        ) from exc

    return DataResult(
        seeded=report.seeded,
        counts=report.counts,
        message=f"Imported the workbook: {_summary(report.counts)}",
    )


@router.post("/reset", response_model=DataResult, dependencies=[ADMIN_ONLY])
def reset(mode: str | None = None) -> DataResult:
    """Empty the books and start again. Admin only.

    Mode is ``fresh`` (starter chart of accounts), ``workbook`` (the sample
    workbook), or ``none``. Defaults to the deployment's configured seed mode.
    """
    if mode not in {None, "fresh", "workbook", "none"}:
        raise DomainError("mode must be one of: fresh, workbook, none")

    report = service.reset(mode)
    return DataResult(
        seeded=report.seeded,
        counts=report.counts,
        message=f"Reset to {mode or 'the configured start'}: {_summary(report.counts)}",
    )


def _summary(counts: dict[str, int]) -> str:
    """A short human-readable count summary."""
    if not counts:
        return "no data"
    return ", ".join(f"{value} {key.replace('_', ' ')}" for key, value in counts.items())
