"""Pydantic schemas for the report module."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.core.enums import AccountType, Segment


class AccountBalance(BaseModel):
    """One account's opening, period, and closing movement."""

    account_code: str
    account_name: str
    account_type: AccountType
    segment: Segment
    opening_debit: Decimal
    opening_credit: Decimal
    period_debit: Decimal
    period_credit: Decimal
    closing_debit: Decimal
    closing_credit: Decimal


class GeneralLedgerOut(BaseModel):
    """General ledger for a date range."""

    date_from: date
    date_to: date
    accounts: list[AccountBalance]
    total_period_debit: Decimal
    total_period_credit: Decimal


class TrialBalanceRow(BaseModel):
    """A single trial-balance line."""

    account_code: str
    account_name: str
    account_type: AccountType
    segment: Segment
    debit: Decimal
    credit: Decimal


class TrialBalanceOut(BaseModel):
    """Trial balance as of a date, with the netting check."""

    as_of: date
    rows: list[TrialBalanceRow]
    total_debit: Decimal
    total_credit: Decimal
    difference: Decimal
    balanced: bool


class SegmentPnlRow(BaseModel):
    """One segment's revenue, cost, and margin."""

    segment: str
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    gross_margin_pct: Decimal


class PnlOut(BaseModel):
    """Profit and loss by segment, plus company-wide totals."""

    date_from: date
    date_to: date
    segments: list[SegmentPnlRow]
    total_revenue: Decimal
    total_cogs: Decimal
    total_gross_profit: Decimal
    gross_margin_pct: Decimal
    operating_expenses: Decimal
    other_income: Decimal
    net_profit: Decimal


class BalanceSheetOut(BaseModel):
    """Balance sheet as of a date, with the balancing check."""

    as_of: date
    assets: list[TrialBalanceRow]
    liabilities: list[TrialBalanceRow]
    equity_accounts: list[TrialBalanceRow]
    total_assets: Decimal
    total_liabilities: Decimal
    equity_per_gl: Decimal
    current_period_profit: Decimal
    total_equity: Decimal
    total_liabilities_and_equity: Decimal
    check: Decimal
    is_balanced: bool


class IntegrityCheck(BaseModel):
    """A single data-integrity assertion."""

    name: str
    passed: bool
    detail: str
    value: Decimal | None = None


class IntegrityReport(BaseModel):
    """The full set of integrity assertions shown on the dashboard."""

    checks: list[IntegrityCheck]
    all_passed: bool
