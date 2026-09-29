"""Business logic for the approval workflow."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ApprovalRequiredError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.approvals import policy, repository
from app.modules.approvals.models import APPROVED, PENDING, REJECTED, ApprovalRequest
from app.modules.users_roles.models import User
from app.modules.users_roles.service import is_allowed, resource_label


def _now() -> dt.datetime:
    """Current UTC time."""
    return dt.datetime.now(dt.timezone.utc)


def create_request(
    db: Session,
    *,
    source_type: str,
    source_id: int,
    action: str,
    amount: Decimal | None,
    reason: str,
    requested_by: str,
) -> ApprovalRequest:
    """Record a pending request, or return the one already waiting."""
    existing = repository.find_pending(db, source_type, source_id, action)
    if existing is not None:
        return existing
    return repository.add(
        db,
        ApprovalRequest(
            source_type=source_type,
            source_id=source_id,
            action=action,
            amount=amount,
            reason=reason,
            requested_by=requested_by,
            status=PENDING,
        ),
    )


def gate(
    db: Session,
    *,
    source_type: str,
    source_id: int,
    action: str,
    amount: Decimal | None,
    reason: str,
    requested_by: str,
) -> None:
    """Pause an action the policy covers, recording a request.

    Raises :class:`ApprovalRequiredError` after the request is committed, so the
    paused action is never lost when the caller's transaction is rolled back.
    """
    if not policy.needs_approval(db, action=action, amount=amount):
        return
    request = create_request(
        db,
        source_type=source_type,
        source_id=source_id,
        action=action,
        amount=amount,
        reason=reason,
        requested_by=requested_by,
    )
    db.commit()
    raise ApprovalRequiredError(
        f"This {action} needs a second person's approval. Request #{request.id} "
        f"is waiting on the Approvals screen."
    )


def list_visible(db: Session, user: User) -> list[ApprovalRequest]:
    """Requests the user has the write access to decide, pending ones first."""
    rows = repository.list_requests(db)
    visible = [
        row
        for row in rows
        if is_allowed(user.role, policy.resource_for(row.source_type), write=True)
    ]
    return sorted(visible, key=lambda row: (row.status != PENDING, -row.id))


def _check_decider(db: Session, request: ApprovalRequest, user: User) -> None:
    """Refuse a decision the user is not allowed to make."""
    if request.status != PENDING:
        raise DomainError(f"Request #{request.id} is already {request.status}.")
    resource = policy.resource_for(request.source_type)
    if not is_allowed(user.role, resource, write=True):
        raise PermissionDeniedError(
            f"Deciding a {request.source_type} {request.action} needs write access "
            f"to the {resource_label(resource)} area."
        )
    if request.requested_by.lower() == user.email.lower():
        raise PermissionDeniedError(
            "You cannot approve your own request; a second person must decide it."
        )


def _execute(db: Session, request: ApprovalRequest, decided_by: str) -> None:
    """Perform the action that was paused, as the approver."""
    if request.action != "reverse":
        raise DomainError(f"Unsupported approval action: {request.action}")

    if request.source_type == "sale":
        from app.modules.sales import service as sales

        sales.reverse(
            db,
            request.source_id,
            reason=request.reason,
            posted_by=decided_by,
            bypass_approval=True,
        )
    elif request.source_type == "purchase":
        from app.modules.purchases import service as purchases

        purchases.reverse(
            db,
            request.source_id,
            reason=request.reason,
            posted_by=decided_by,
            bypass_approval=True,
        )
    elif request.source_type == "production":
        from app.modules.production import service as production

        production.reverse(
            db,
            request.source_id,
            reason=request.reason,
            posted_by=decided_by,
            bypass_approval=True,
        )
    elif request.source_type == "payroll":
        from app.modules.payroll import service as payroll

        payroll.reverse(
            db,
            request.source_id,
            reason=request.reason,
            posted_by=decided_by,
            bypass_approval=True,
        )
    else:
        raise DomainError(f"Unknown approval source: {request.source_type}")


def approve(
    db: Session, request_id: int, user: User, note: str | None = None
) -> ApprovalRequest:
    """Approve a request and perform the action it held back."""
    request = repository.get(db, request_id)
    if request is None:
        raise NotFoundError(f"Approval request {request_id} not found")

    _check_decider(db, request, user)
    _execute(db, request, user.email)

    request.status = APPROVED
    request.decided_by = user.email
    request.decided_at = _now()
    request.note = note
    db.commit()
    return request


def reject(
    db: Session, request_id: int, user: User, note: str | None = None
) -> ApprovalRequest:
    """Reject a request. The paused action simply does not happen."""
    request = repository.get(db, request_id)
    if request is None:
        raise NotFoundError(f"Approval request {request_id} not found")

    _check_decider(db, request, user)
    request.status = REJECTED
    request.decided_by = user.email
    request.decided_at = _now()
    request.note = note
    db.commit()
    return request
