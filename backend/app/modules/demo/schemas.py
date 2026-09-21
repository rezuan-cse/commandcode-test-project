"""Schemas for demo housekeeping."""

from __future__ import annotations

from pydantic import BaseModel


class ResetResult(BaseModel):
    """Outcome of a demo reset."""

    seeded: bool
    counts: dict[str, int]
    message: str
