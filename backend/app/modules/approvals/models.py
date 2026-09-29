"""The approval workflow.

When the client switches second-person approval on, an action that the policy
covers is paused: a request is recorded, and a *different* person with write
access to the same area approves it. Approving performs the deferred action.
Off by default, so nothing changes until the rule is turned on in
Administration → Configuration.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"


class ApprovalRequest(Base):
    """A paused action waiting for a second person's decision."""

    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[int] = mapped_column(nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    reason: Mapped[str] = mapped_column(String(400), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=PENDING, nullable=False)
    decided_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
