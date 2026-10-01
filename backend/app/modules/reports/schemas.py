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


class PeriodSpan(BaseModel):
    """One of the two periods being compared."""

    date_from: date
    date_to: date


class PnlLineComparison(BaseModel):
    """One figure in both periods, with the movement between them.

    ``change_pct`` is **empty, not zero**, when the earlier period had nothing in
    it: a percentage change against zero is not a number, and reporting one would
    be inventing it. The absolute change is still given, because "nothing last
    time, 4,000 this time" is exactly what the reader needs to see.
    """

    metric: str
    period_1: Decimal
    period_2: Decimal
    change: Decimal
    change_pct: Decimal | None = None
    # True for a figure that is already a percentage (a margin), where a percentage
    # *change* would be meaningless. The change shown is then in points.
    is_percentage: bool = False


class SegmentComparison(BaseModel):
    """One segment's comparison, or the company total in the same shape."""

    segment: str
    lines: list[PnlLineComparison]


class PnlComparisonOut(BaseModel):
    """Two periods side by side, with the movement between them."""

    period_1: PeriodSpan
    period_2: PeriodSpan
    total: SegmentComparison
    segments: list[SegmentComparison]


class LowStockRow(BaseModel):
    """An item at or below its reorder level, and the cost of topping it back up."""

    code: str
    name: str
    category: str
    segment: str
    uom: str
    qty_on_hand: Decimal
    reorder_level: Decimal
    shortfall: Decimal
    avg_cost: Decimal
    value_on_hand: Decimal
    # What the shortfall would cost at the current average cost — the figure that
    # turns a reorder list into a purchase decision.
    reorder_value: Decimal


class LowStockOut(BaseModel):
    """The reorder list, most needed first."""

    as_of: date
    rows: list[LowStockRow]
    total_reorder_value: Decimal


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
