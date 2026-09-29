"""Pydantic schemas for data administration."""

from __future__ import annotations

from pydantic import BaseModel


class DataResult(BaseModel):
    """The outcome of an import or a reset."""

    seeded: bool
    counts: dict[str, int]
    message: str
