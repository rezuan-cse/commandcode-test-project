"""Business logic for the settings store.

Values are stored as JSON-encoded strings in one table; the shape each value must
take comes from the catalogue in :mod:`catalog`. Business logic reads them through
the typed getters below, so a rate or a switch is never hardcoded and never read
by guessing at the string form.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError, NotFoundError
from app.modules.settings.catalog import (
    CATALOG_BY_KEY,
    GROUP_ORDER,
    SettingSpec,
)
from app.modules.settings.models import Setting
from app.modules.settings.schemas import SettingOut, SettingUpdate

_TRUE = {"true", "1", "yes", "on"}
_FALSE = {"false", "0", "no", "off"}


def seed_defaults(db: Session) -> None:
    """Insert any missing setting. Idempotent.

    A value the client has already confirmed is inserted as confirmed; everything
    else is flagged pending. An existing row is never overwritten, so a value
    someone has edited is not quietly reset on the next boot.
    """
    existing = {key for (key,) in db.execute(select(Setting.key)).all()}
    for spec in CATALOG_BY_KEY.values():
        if spec.key in existing:
            continue
        db.add(
            Setting(
                key=spec.key,
                value=json.dumps(spec.default),
                description=spec.description,
                confirmed_by_client=spec.confirmed,
            )
        )
    db.flush()


def _to_out(setting: Setting) -> SettingOut:
    """Join a stored value with its catalogue metadata for the interface."""
    spec = CATALOG_BY_KEY.get(setting.key)
    return SettingOut(
        key=setting.key,
        value=setting.value,
        description=setting.description,
        confirmed_by_client=setting.confirmed_by_client,
        group=spec.group if spec else "other",
        label=spec.label if spec else setting.key,
        value_type=spec.value_type if spec else "string",
        options=spec.options if spec else None,
        sort_order=spec.sort_order if spec else 0,
    )


def _order_key(setting: Setting) -> tuple[int, int, str]:
    """Group order, then position within the group, then key."""
    spec = CATALOG_BY_KEY.get(setting.key)
    group = spec.group if spec else "other"
    rank = GROUP_ORDER.index(group) if group in GROUP_ORDER else len(GROUP_ORDER)
    return (rank, spec.sort_order if spec else 0, setting.key)


def list_settings(db: Session) -> list[SettingOut]:
    """Return every setting, ordered the way the editor shows them."""
    rows = list(db.execute(select(Setting)).scalars().all())
    return [_to_out(row) for row in sorted(rows, key=_order_key)]


def _canonical(spec: SettingSpec, raw: str) -> str:
    """Validate a submitted value against its spec and return the stored form."""
    kind = spec.value_type
    try:
        if kind == "bool":
            text = raw.strip().lower()
            if text in _TRUE:
                parsed: object = True
            elif text in _FALSE:
                parsed = False
            else:
                parsed = bool(json.loads(raw))
        elif kind == "number":
            parsed = str(Decimal(raw.strip()))
        elif kind == "enum":
            parsed = raw
            if spec.options and parsed not in spec.options:
                raise DomainError(
                    f"{spec.key} must be one of: {', '.join(spec.options)}"
                )
        elif kind == "json":
            parsed = json.loads(raw)
        else:
            parsed = raw
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise DomainError(f"{spec.key} expects a {kind} value") from exc
    return json.dumps(parsed)


def update_setting(db: Session, key: str, payload: SettingUpdate) -> SettingOut:
    """Update one setting, validating the value against its catalogue entry."""
    setting = db.get(Setting, key)
    if setting is None:
        raise NotFoundError(f"Setting {key} not found")

    spec = CATALOG_BY_KEY.get(key)
    if spec is None:
        # A key with no catalogue entry is stored as a plain string.
        setting.value = json.dumps(payload.value)
    else:
        setting.value = _canonical(spec, payload.value)

    if payload.confirmed_by_client is not None:
        setting.confirmed_by_client = payload.confirmed_by_client
    db.commit()
    return _to_out(setting)


# --- Typed getters, used by business logic --------------------------------


def _parsed(db: Session, key: str) -> object:
    """Read a value and decode it, falling back to the catalogue default."""
    row = db.get(Setting, key)
    if row is None:
        spec = CATALOG_BY_KEY.get(key)
        return spec.default if spec else None
    try:
        return json.loads(row.value)
    except (ValueError, TypeError):
        return row.value


def get_str(db: Session, key: str, default: str = "") -> str:
    """Read a string setting."""
    value = _parsed(db, key)
    return default if value is None else str(value)


def get_bool(db: Session, key: str) -> bool:
    """Read a boolean setting."""
    value = _parsed(db, key)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _TRUE


def get_number(db: Session, key: str) -> Decimal:
    """Read a numeric setting as a :class:`Decimal`."""
    value = _parsed(db, key)
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return Decimal(0)


def get_json(db: Session, key: str) -> object:
    """Read a JSON setting as a decoded object."""
    return _parsed(db, key)


def get_account(db: Session, key: str) -> str:
    """Read an account-code setting as a plain string."""
    return get_str(db, key)
