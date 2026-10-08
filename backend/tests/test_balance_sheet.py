"""Balance-sheet balancing: the sheet must balance across year boundaries.

The balance sheet adds the current year's profit to equity. Profit earned
*before* that year is retained earnings — it sits in the asset and liability
balances, so without a home on the equity side any books spanning more than
one year can never balance. That is pinned down here.

(The test database comes pre-seeded with the sample workbook, so the tests
assert the *movement* caused by the new postings, not absolute figures.)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.modules.journal_entries import service as journal_service
from app.modules.journal_entries.schemas import JournalEntryCreate, JournalLineIn
from app.modules.reports import service as reports

AS_OF = date(2026, 10, 31)


def _sale(voucher: str, when: date, amount: str) -> JournalEntryCreate:
    """A cash sale: debit Cash and Bank, credit Sales Revenue."""
    return JournalEntryCreate(
        voucher_no=voucher,
        entry_date=when,
        narration="test sale",
        lines=[
            JournalLineIn(account_code="1010", segment="Shared", debit=Decimal(amount)),
            JournalLineIn(
                account_code="4010",
                segment="Manufacturing",
                credit=Decimal(amount),
            ),
        ],
    )


def test_prior_year_profit_is_retained_earnings(db) -> None:
    """A sale posted last year lands in retained earnings, a sale this year
    in current-period profit, and the sheet balances."""
    before = reports.balance_sheet(db, AS_OF)
    journal_service.post_manual_entry(db, _sale("S-2025", date(2025, 6, 15), "1000"))
    journal_service.post_manual_entry(db, _sale("S-2026", date(2026, 3, 10), "400"))

    sheet = reports.balance_sheet(db, AS_OF)

    assert sheet.is_balanced
    assert sheet.check == 0
    assert sheet.retained_earnings - before.retained_earnings == Decimal("1000")
    assert sheet.current_period_profit - before.current_period_profit == Decimal("400")
    assert sheet.total_assets == sheet.total_liabilities_and_equity


def test_current_year_sale_needs_no_retained_earnings(db) -> None:
    """A sale this year moves current-period profit only; retained earnings
    are untouched and the sheet stays balanced."""
    before = reports.balance_sheet(db, AS_OF)
    journal_service.post_manual_entry(db, _sale("S-2026", date(2026, 3, 10), "400"))

    sheet = reports.balance_sheet(db, AS_OF)

    assert sheet.is_balanced
    assert sheet.retained_earnings == before.retained_earnings
    assert sheet.current_period_profit - before.current_period_profit == Decimal("400")
