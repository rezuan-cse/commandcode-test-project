"""The approval policy: does an action need a second person, read from settings."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.settings import service as settings_service

# Which permission resource governs each source of an approval request.
_RESOURCE_BY_SOURCE = {
    "sale": "sales_purchase",
    "purchase": "sales_purchase",
    "production": "production",
    "payroll": "payroll",
}


def resource_for(source_type: str) -> str:
    """The resource a decider must have write access to."""
    return _RESOURCE_BY_SOURCE.get(source_type, "journal_entries")


def needs_approval(db: Session, *, action: str, amount: Decimal | None) -> bool:
    """Whether an action is covered by the configured approval policy."""
    if not settings_service.get_bool(db, "posting.require_second_approval"):
        return False

    scope = settings_service.get_str(db, "posting.approval_scope", "reversals")
    if action == "reverse" and scope not in {"reversals", "reversals_and_postings"}:
        return False
    if action == "post" and scope != "reversals_and_postings":
        return False

    threshold = settings_service.get_number(db, "posting.approval_threshold")
    if threshold > 0 and amount is not None and amount < threshold:
        return False
    return True
