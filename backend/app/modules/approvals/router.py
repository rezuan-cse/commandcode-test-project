"""Thin HTTP routes for the approval workflow."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.approvals import service
from app.modules.approvals.schemas import ApprovalDecision, ApprovalOut
from app.modules.auth.dependencies import get_current_user
from app.modules.users_roles.models import User

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut])
def list_approvals(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ApprovalOut]:
    """Requests the signed-in user is able to decide."""
    return service.list_visible(db, user)


@router.post("/{request_id}/approve", response_model=ApprovalOut)
def approve(
    request_id: int,
    payload: ApprovalDecision,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApprovalOut:
    """Approve a request and carry out the action it held back."""
    return service.approve(db, request_id, user, payload.note)


@router.post("/{request_id}/reject", response_model=ApprovalOut)
def reject(
    request_id: int,
    payload: ApprovalDecision,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApprovalOut:
    """Reject a request."""
    return service.reject(db, request_id, user, payload.note)
