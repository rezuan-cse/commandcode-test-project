"""Business logic for the settings store."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.settings.models import Setting
from app.modules.settings.schemas import SettingUpdate

# Defaults for every rule the client has not yet confirmed. Each is flagged so
# the UI can show a "pending client confirmation" badge.
DEFAULT_SETTINGS: list[tuple[str, object, str]] = [
    ("vat.standard_rate_pct", 15, "Standard VAT rate. TBD (client)."),
    ("vat.input_account", "1130", "Input VAT tracking account."),
    ("vat.output_account", "2200", "Output VAT tracking account."),
    ("tax.ait_rate_pct", 5, "Advance income tax rate. TBD (client)."),
    ("tax.tds_rate_pct", 5, "Tax deducted at source rate. TBD (client)."),
    ("payroll.pay_frequency", "monthly", "Payroll frequency. TBD (client)."),
    ("payroll.statutory_deduction_pct", 10, "Statutory deduction percentage. TBD (client)."),
    ("inventory.costing_method", "weighted_average", "Inventory costing method."),
    ("posting.require_second_approval", False, "Whether postings need approval. TBD (client)."),
    ("security.require_2fa", False, "Whether login requires 2FA. TBD (client)."),
]


def seed_defaults(db: Session) -> None:
    """Insert any missing default settings. Idempotent."""
    existing = {key for (key,) in db.execute(select(Setting.key)).all()}
    for key, value, description in DEFAULT_SETTINGS:
        if key in existing:
            continue
        db.add(
            Setting(
                key=key,
                value=json.dumps(value),
                description=description,
                confirmed_by_client=False,
            )
        )
    db.flush()


def list_settings(db: Session) -> list[Setting]:
    """Return all settings ordered by key."""
    return list(db.execute(select(Setting).order_by(Setting.key)).scalars().all())


def update_setting(db: Session, key: str, payload: SettingUpdate) -> Setting:
    """Update one setting's value."""
    setting = db.get(Setting, key)
    if setting is None:
        raise NotFoundError(f"Setting {key} not found")
    setting.value = payload.value
    if payload.confirmed_by_client is not None:
        setting.confirmed_by_client = payload.confirmed_by_client
    db.commit()
    return setting
