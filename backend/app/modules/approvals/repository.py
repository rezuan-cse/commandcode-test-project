"""Data access for approval requests."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.approvals.models import PENDING, ApprovalRequest


def add(db: Session, request: ApprovalRequest) -> ApprovalRequest:
    """Persist a new request."""
    db.add(request)
    db.flush()
    return request


def get(db: Session, request_id: int) -> ApprovalRequest | None:
    """Fetch one request."""
    return db.get(ApprovalRequest, request_id)


def find_pending(db: Session, source_type: str, source_id: int, action: str) -> ApprovalRequest | None:
    """An existing pending request for the same action, if there is one."""
    stmt = select(ApprovalRequest).where(
        ApprovalRequest.source_type == source_type,
        ApprovalRequest.source_id == source_id,
        ApprovalRequest.action == action,
        ApprovalRequest.status == PENDING,
    )
    return db.execute(stmt).scalars().first()


def list_requests(db: Session, status: str | None = None) -> list[ApprovalRequest]:
    """List requests, newest first, optionally filtered by status."""
    stmt = select(ApprovalRequest).order_by(ApprovalRequest.id.desc())
    if status:
        stmt = stmt.where(ApprovalRequest.status == status)
    return list(db.execute(stmt).scalars().all())
