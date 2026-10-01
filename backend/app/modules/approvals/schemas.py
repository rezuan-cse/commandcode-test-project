"""Pydantic schemas for the approval workflow."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.clock import LocalDateTime


class ApprovalOut(BaseModel):
    """A paused action, as shown on the Approvals screen."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: str
    source_id: int
    action: str
    amount: Decimal | None
    reason: str
    requested_by: str
    status: str
    decided_by: str | None
    decided_at: LocalDateTime | None
    note: str | None
    created_at: LocalDateTime


class ApprovalDecision(BaseModel):
    """A decision on a pending request, with an optional note."""

    note: str | None = Field(default=None, max_length=400)
