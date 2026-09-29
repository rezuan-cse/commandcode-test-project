"""VAT and withholding tax for transactions.

Nothing here is hardcoded: the rate, the accounts, which segments carry VAT and
whether it is inclusive all come from the `settings` table. With VAT switched off
(the default until the client confirms the rules) every function returns the
input unchanged and no tax line is posted.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.money import money, ZERO
from app.modules.journal_entries.models import JournalEntry, JournalLine
from app.modules.settings import service as settings_service

HUNDRED = Decimal("100")


def _rate(db: Session) -> Decimal:
    """The standard VAT rate as a fraction (15% -> 0.15)."""
    return settings_service.get_number(db, "vat.standard_rate_pct") / HUNDRED


def charge_vat(db: Session) -> bool:
    """Whether VAT is switched on at all."""
    return settings_service.get_bool(db, "vat.charge_vat")


def output_account(db: Session) -> str:
    """The account output VAT is credited to."""
    return settings_service.get_account(db, "vat.output_account")


def input_account(db: Session) -> str:
    """The account input VAT is debited to."""
    return settings_service.get_account(db, "vat.input_account")


def account_name(db: Session, code: str) -> str:
    """Look up an account's display name, falling back to its code."""
    from app.modules.accounts import repository as accounts_repo

    account = accounts_repo.get_account(db, code)
    return account.name_en if account else code


def _segments(db: Session) -> set[str]:
    value = settings_service.get_json(db, "vat.applies_to_segments")
    return {str(v) for v in value} if isinstance(value, list) else set()


def _zero_rated(db: Session) -> set[str]:
    value = settings_service.get_json(db, "vat.zero_rated_items")
    return {str(v) for v in value} if isinstance(value, list) else set()


def applies(db: Session, *, segment: str, item_code: str) -> bool:
    """Whether VAT applies to a line, given the switch, segment and item."""
    if not charge_vat(db) or _rate(db) <= 0:
        return False
    if item_code in _zero_rated(db):
        return False
    segments = _segments(db)
    return not segments or segment in segments


def sale_split(
    db: Session, *, segment: str, item_code: str, gross: Decimal
) -> tuple[Decimal, Decimal]:
    """Split a sale line into (net revenue, VAT).

    ``gross`` is the amount on the line as entered. When prices are entered
    VAT-inclusive the tax is backed out; otherwise it is added on top.
    """
    gross = money(gross)
    if not applies(db, segment=segment, item_code=item_code):
        return gross, ZERO
    rate = _rate(db)
    if settings_service.get_bool(db, "vat.prices_include_vat"):
        net = money(gross / (1 + rate))
        return net, money(gross - net)
    return gross, money(gross * rate)


def purchase_vat(
    db: Session, *, segment: str, item_code: str, net: Decimal
) -> Decimal:
    """The input VAT on a purchase line, or zero when it is not recoverable."""
    if not applies(db, segment=segment, item_code=item_code):
        return ZERO
    if not settings_service.get_bool(db, "vat.input_recoverable"):
        return ZERO
    return money(money(net) * _rate(db))


def _balance(db: Session, account: str, date_from: date, date_to: date) -> Decimal:
    """Net movement on an account over a period: debits minus credits."""
    rows = db.execute(
        select(JournalLine.debit, JournalLine.credit)
        .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
        .where(
            JournalEntry.entry_date >= date_from,
            JournalEntry.entry_date <= date_to,
            JournalLine.account_code == account,
        )
    ).all()
    debits = sum((money(row[0]) for row in rows), ZERO)
    credits = sum((money(row[1]) for row in rows), ZERO)
    return money(debits - credits)


def summary(db: Session, date_from: date, date_to: date) -> dict[str, Decimal]:
    """Output VAT, input VAT and net payable over a period."""
    output = money(-_balance(db, output_account(db), date_from, date_to))
    input_vat = _balance(db, input_account(db), date_from, date_to)
    return {
        "output_vat": output,
        "input_vat": input_vat,
        "net_payable": money(output - input_vat),
    }
