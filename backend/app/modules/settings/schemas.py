"""Pydantic schemas for the settings module."""

from __future__ import annotations

from pydantic import BaseModel


class SettingOut(BaseModel):
    """A configuration entry, with the metadata the editor needs to render it."""

    key: str
    value: str
    description: str | None
    confirmed_by_client: bool
    group: str
    label: str
    value_type: str
    options: list[str] | None = None
    sort_order: int = 0


class SettingUpdate(BaseModel):
    """Payload for updating a configuration value.

    ``value`` is sent as a string and parsed according to the entry's
    ``value_type``: a number, a boolean, an enum member, or JSON.
    """

    value: str
    confirmed_by_client: bool | None = None
