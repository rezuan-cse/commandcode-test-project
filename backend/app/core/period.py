"""Accounting periods, derived from configuration rather than assumed.

Bangladesh runs a July–June fiscal year. The balance sheet used to assume a
calendar year, which put profit earned in July–December into the previous year's
retained earnings and split a single trading year across two "current periods".
That is invisible while every figure is zero, and wrong the moment there are any.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

# 1 July, for a Bangladesh company.
DEFAULT_FISCAL_START_MONTH = 7


def fiscal_year_start(as_of: date, start_month: int) -> date:
    """The first day of the fiscal year containing ``as_of``.

    A month outside 1–12 is clamped rather than raising: a bad setting should give
    a defensible period, not break every report.
    """
    month = min(max(int(start_month), 1), 12)
    year = as_of.year if as_of.month >= month else as_of.year - 1
    return date(year, month, 1)


def fiscal_start_for(db: Session, as_of: date) -> date:
    """The fiscal year start configured for this company."""
    from app.modules.settings import service as settings_service

    month = int(settings_service.get_number(db, "company.fiscal_year_start_month"))
    return fiscal_year_start(as_of, month)
