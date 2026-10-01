"""Time.

Timestamps are **stored in UTC** and **shown at a fixed offset** from it — GMT+6
by default, which is what the client works in. Bangladesh has no daylight saving,
so a fixed offset is exact as well as simple.

Storing UTC keeps the books unambiguous: a date written now means the same instant
wherever the service is later hosted. The offset is applied at the edge, when a
value is handed to the interface, so every screen shows the same clock.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated

from pydantic import PlainSerializer

from app.core.config import settings


def utc_now() -> dt.datetime:
    """The current instant, as an aware UTC datetime, for storage."""
    return dt.datetime.now(dt.timezone.utc)


def local_zone() -> dt.timezone:
    """The zone timestamps are shown in."""
    return dt.timezone(dt.timedelta(hours=settings.utc_offset_hours))


def as_local(value: dt.datetime | None) -> dt.datetime | None:
    """Take a stored timestamp and express it on the client's clock.

    A stored value is naive UTC — the columns hold no zone — so a naive value is
    read as UTC. One that already carries a zone is converted from it.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(local_zone())


def local_label(value: dt.datetime | None) -> str | None:
    """A timestamp as the interface should read it: 2026-10-01T14:25:09+06:00."""
    local = as_local(value)
    return None if local is None else local.isoformat(timespec="seconds")


# A timestamp field that serialises to the client's clock. Use it on every
# datetime a response carries, so no screen has to know about the offset.
LocalDateTime = Annotated[
    dt.datetime, PlainSerializer(local_label, return_type=str, when_used="json")
]
