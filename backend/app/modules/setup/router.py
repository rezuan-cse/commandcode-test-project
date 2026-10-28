"""HTTP routes for first-run setup."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.setup import service
from app.modules.setup.schemas import (
    SetupAdminRequest,
    SetupChecklist,
    SetupResult,
    SetupState,
)

router = APIRouter(prefix="/setup", tags=["setup"])

ANY_SIGNED_IN = Depends(get_current_user)


@router.get("/state", response_model=SetupState)
def setup_state(db: Session = Depends(get_db)) -> SetupState:
    """Whether the system still needs its first administrator.

    Public on purpose: this is what the sign-in screen asks before a session can
    exist. It reveals only whether the user table is empty and the company's name.
    """
    return service.state(db)


@router.post("/admin", response_model=SetupResult, status_code=201)
def create_first_admin(
    payload: SetupAdminRequest, db: Session = Depends(get_db)
) -> SetupResult:
    """Create the first administrator and sign them in.

    Refused with 409 once any account exists, so it cannot mint extra
    administrators later. After that, accounts are made from Roles & Access.
    """
    session = service.create_first_admin(db, payload)
    return SetupResult(
        **session.model_dump(),
        message=(
            "Administrator created. Add your company details next — the Dashboard "
            "checklist walks through the rest."
        ),
    )


@router.get(
    "/checklist", response_model=SetupChecklist, dependencies=[ANY_SIGNED_IN]
)
def setup_checklist(db: Session = Depends(get_db)) -> SetupChecklist:
    """The steps from an empty system to a first sale, and which are done."""
    return service.checklist(db)
