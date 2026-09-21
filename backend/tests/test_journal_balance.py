"""Journal-entry rules: the books can never be left unbalanced."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import DuplicateError, UnbalancedEntryError
from app.modules.journal_entries import service as journal_service
from app.modules.journal_entries.schemas import JournalEntryCreate, JournalLineIn

POSTING_DATE = date(2026, 10, 5)


def _entry(voucher: str, debit: str, credit: str) -> JournalEntryCreate:
    """Build a simple two-line entry with explicit amounts."""
    return JournalEntryCreate(
        voucher_no=voucher,
        entry_date=POSTING_DATE,
        narration="test",
        lines=[
            JournalLineIn(account_code="1010", segment="Shared", debit=Decimal(debit)),
            JournalLineIn(account_code="4010", segment="Manufacturing", credit=Decimal(credit)),
        ],
    )


def test_balanced_entry_posts(db) -> None:
    """A balanced two-line entry commits and is retrievable."""
    posted = journal_service.post_manual_entry(db, _entry("JRN-001", "500", "500"))
    assert posted.id is not None
    fetched = journal_service.get_entry(db, posted.id)
    assert len(fetched.lines) == 2


def test_unbalanced_entry_is_rejected(db) -> None:
    """Debits that do not match credits are refused before touching the database."""
    with pytest.raises(UnbalancedEntryError):
        journal_service.post_manual_entry(db, _entry("JRN-002", "500", "400"))


def test_duplicate_voucher_is_rejected(db) -> None:
    """The same voucher number cannot be posted twice."""
    journal_service.post_manual_entry(db, _entry("JRN-003", "250", "250"))
    with pytest.raises(DuplicateError):
        journal_service.post_manual_entry(db, _entry("JRN-003", "250", "250"))


def test_line_cannot_be_both_debit_and_credit() -> None:
    """A single line must be one side only."""
    with pytest.raises(ValueError):
        JournalLineIn(
            account_code="1010",
            segment="Shared",
            debit=Decimal("10"),
            credit=Decimal("10"),
        )


def test_balanced_entry_keeps_trial_balance_at_zero(db) -> None:
    """Posting a valid entry does not disturb the trial balance."""
    journal_service.post_manual_entry(db, _entry("JRN-004", "1234.56", "1234.56"))
    from app.modules.reports import service as reports

    tb = reports.trial_balance(db, POSTING_DATE)
    assert tb.difference == 0
    assert tb.balanced is True
