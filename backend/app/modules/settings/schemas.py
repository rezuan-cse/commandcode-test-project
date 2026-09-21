"""Pydantic schemas for the settings module."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SettingOut(BaseModel):
    """A configuration entry."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    value: str
    description: str | None
    confirmed_by_client: bool


class SettingUpdate(BaseModel):
    """Payload for updating a configuration value."""

    value: str
    confirmed_by_client: bool | None = None
