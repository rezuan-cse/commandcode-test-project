"""Report computation. Everything is derived live; nothing is stored twice."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import AccountType, Segment
from app.core.money import money, to_decimal, ZERO
from app.modules.inventory_ledger import service as ledger
from app.modules.items_bom import repository as items_repo
from app.modules.reports import repository as repo
from app.modules.reports.schemas import (
    AccountBalance,
    BalanceSheetOut,
    GeneralLedgerOut,
    IntegrityCheck,
    IntegrityReport,
    PnlOut,
    SegmentPnlRow,
    TrialBalanceOut,
    TrialBalanceRow,
)

SEGMENTS = [
    Segment.IMPORT,
    Segment.MANUFACTURING,
    Segment.PACKAGING,
    Segment.TRADING,
    Segment.APPLICATION,
]


def _signed(value: Decimal, value_type: AccountType) -> Decimal:
    """Return a value with its natural-balance sign applied (positive = natural)."""
    if value_type in {AccountType.ASSET, AccountType.COGS, AccountType.EXPENSE}:
        return value
    return -value


def general_ledger(db: Session, date_from: date, date_to: date) -> GeneralLedgerOut:
    """Opening + period + closing movement per account, for a date range."""
    movements = repo.Movements()
    for opening in repo.opening_balances(db):
        bucket = movements.get(opening.account_code)
        bucket.opening_debit = money(bucket.opening_debit + to_decimal(opening.debit))
        bucket.opening_credit = money(bucket.opening_credit + to_decimal(opening.credit))

    for line, _entry_date, _source in repo.period_lines(db, date_from, date_to):
        bucket = movements.get(line.account_code)
        bucket.period_debit = money(bucket.period_debit + to_decimal(line.debit))
        bucket.period_credit = money(bucket.period_credit + to_decimal(line.credit))

    accounts: list[AccountBalance] = []
    total_debit = ZERO
    total_credit = ZERO
    for account in repo.all_accounts(db):
        bucket = movements.get(account.code)
        net = (bucket.opening_debit - bucket.opening_credit) + (
            bucket.period_debit - bucket.period_credit
        )
        closing_debit = money(net) if net > 0 else ZERO
        closing_credit = money(-net) if net < 0 else ZERO
        total_debit = money(total_debit + bucket.period_debit)
        total_credit = money(total_credit + bucket.period_credit)
        accounts.append(
            AccountBalance(
                account_code=account.code,
                account_name=account.name_en,
                account_type=account.account_type,
                segment=account.segment,
                opening_debit=bucket.opening_debit,
                opening_credit=bucket.opening_credit,
                period_debit=bucket.period_debit,
                period_credit=bucket.period_credit,
                closing_debit=closing_debit,
                closing_credit=closing_credit,
            )
        )

    return GeneralLedgerOut(
        date_from=date_from,
        date_to=date_to,
        accounts=accounts,
        total_period_debit=total_debit,
        total_period_credit=total_credit,
    )


def _net_balance(db: Session, as_of: date) -> dict[str, Decimal]:
    """Net balance per account (debit-positive) as of a date."""
    balances: dict[str, Decimal] = {}
    for opening in repo.opening_balances(db):
        balances[opening.account_code] = money(
            balances.get(opening.account_code, ZERO)
            + to_decimal(opening.debit)
            - to_decimal(opening.credit)
        )
    for line, _entry_date, _source in repo.period_lines(db, None, as_of):
        balances[line.account_code] = money(
            balances.get(line.account_code, ZERO) + to_decimal(line.debit) - to_decimal(line.credit)
        )
    return balances


def trial_balance(db: Session, as_of: date) -> TrialBalanceOut:
    """Trial balance as of a date, with the balancing difference."""
    balances = _net_balance(db, as_of)
    rows: list[TrialBalanceRow] = []
    total_debit = ZERO
    total_credit = ZERO
    for account in repo.all_accounts(db):
        net = balances.get(account.code, ZERO)
        debit = money(net) if net > 0 else ZERO
        credit = money(-net) if net < 0 else ZERO
        if debit == 0 and credit == 0:
            continue
        total_debit = money(total_debit + debit)
        total_credit = money(total_credit + credit)
        rows.append(
            TrialBalanceRow(
                account_code=account.code,
                account_name=account.name_en,
                account_type=account.account_type,
                segment=account.segment,
                debit=debit,
                credit=credit,
            )
        )
    difference = money(total_debit - total_credit)
    return TrialBalanceOut(
        as_of=as_of,
        rows=rows,
        total_debit=total_debit,
        total_credit=total_credit,
        difference=difference,
        balanced=difference == 0,
    )


def _segment_totals(
    db: Session, date_from: date | None, date_to: date | None
) -> tuple[dict[Segment, dict[str, Decimal]], Decimal, Decimal, Decimal]:
    """Accumulate revenue, COGS, expense, and other income by segment."""
    per_segment: dict[Segment, dict[str, Decimal]] = {
        segment: {"revenue": ZERO, "cogs": ZERO} for segment in SEGMENTS
    }
    expenses = ZERO
    other_income = ZERO
    for line, account_type in repo.period_lines_by_segment(db, date_from, date_to):
        amount = to_decimal(line.debit) - to_decimal(line.credit)
        if account_type == AccountType.REVENUE:
            bucket = per_segment.setdefault(
                line.segment, {"revenue": ZERO, "cogs": ZERO}
            )
            bucket["revenue"] = money(bucket["revenue"] + (-amount))
        elif account_type == AccountType.COGS:
            bucket = per_segment.setdefault(
                line.segment, {"revenue": ZERO, "cogs": ZERO}
            )
            bucket["cogs"] = money(bucket["cogs"] + amount)
        elif account_type == AccountType.EXPENSE:
            expenses = money(expenses + amount)
        elif account_type == AccountType.OTHER_INCOME:
            other_income = money(other_income + (-amount))
    return per_segment, expenses, other_income, ZERO


def pnl_by_segment(db: Session, date_from: date, date_to: date) -> PnlOut:
    """Profit and loss by segment, plus company-wide totals and net profit."""
    per_segment, expenses, other_income, _ = _segment_totals(db, date_from, date_to)
    rows: list[SegmentPnlRow] = []
    total_revenue = ZERO
    total_cogs = ZERO
    for segment in SEGMENTS:
        bucket = per_segment.get(segment, {"revenue": ZERO, "cogs": ZERO})
        revenue = money(bucket["revenue"])
        cogs = money(bucket["cogs"])
        gross = money(revenue - cogs)
        margin = money(gross / revenue * 100) if revenue else ZERO
        total_revenue = money(total_revenue + revenue)
        total_cogs = money(total_cogs + cogs)
        rows.append(
            SegmentPnlRow(
                segment=segment.value,
                revenue=revenue,
                cogs=cogs,
                gross_profit=gross,
                gross_margin_pct=margin,
            )
        )
    total_gross = money(total_revenue - total_cogs)
    overall_margin = money(total_gross / total_revenue * 100) if total_revenue else ZERO
    net_profit = money(total_gross - expenses + other_income)
    return PnlOut(
        date_from=date_from,
        date_to=date_to,
        segments=rows,
        total_revenue=total_revenue,
        total_cogs=total_cogs,
        total_gross_profit=total_gross,
        gross_margin_pct=overall_margin,
        operating_expenses=expenses,
        other_income=other_income,
        net_profit=net_profit,
    )


def balance_sheet(db: Session, as_of: date) -> BalanceSheetOut:
    """Balance sheet as of a date, with the A - L - E check."""
    balances = _net_balance(db, as_of)
    assets: list[TrialBalanceRow] = []
    liabilities: list[TrialBalanceRow] = []
    equity: list[TrialBalanceRow] = []
    total_assets = ZERO
    total_liabilities = ZERO
    equity_gl = ZERO

    for account in repo.all_accounts(db):
        net = balances.get(account.code, ZERO)
        if net == 0:
            continue
        row = TrialBalanceRow(
            account_code=account.code,
            account_name=account.name_en,
            account_type=account.account_type,
            segment=account.segment,
            debit=money(net) if net > 0 else ZERO,
            credit=money(-net) if net < 0 else ZERO,
        )
        if account.account_type == AccountType.ASSET:
            assets.append(row)
            total_assets = money(total_assets + net)
        elif account.account_type == AccountType.LIABILITY:
            liabilities.append(row)
            total_liabilities = money(total_liabilities + (-net))
        elif account.account_type == AccountType.EQUITY:
            equity.append(row)
            equity_gl = money(equity_gl + (-net))

    current_year = date(as_of.year, 1, 1)
    pnl = pnl_by_segment(db, current_year, as_of)
    total_equity = money(equity_gl + pnl.net_profit)
    total_le = money(total_liabilities + total_equity)
    check = money(total_assets - total_le)

    return BalanceSheetOut(
        as_of=as_of,
        assets=assets,
        liabilities=liabilities,
        equity_accounts=equity,
        total_assets=money(total_assets),
        total_liabilities=money(total_liabilities),
        equity_per_gl=equity_gl,
        current_period_profit=pnl.net_profit,
        total_equity=total_equity,
        total_liabilities_and_equity=total_le,
        check=check,
        is_balanced=check == 0,
    )


def integrity_report(db: Session, as_of: date) -> IntegrityReport:
    """The data-integrity assertions shown on the demo dashboard."""
    tb = trial_balance(db, as_of)
    bs = balance_sheet(db, as_of)

    gl_inventory = ZERO
    for row in tb.rows:
        if row.account_code.startswith("12") and row.account_code != "1260":
            gl_inventory = money(gl_inventory + row.debit - row.credit)

    ledger_total = ZERO
    for item in items_repo.list_items(db):
        position = ledger.position(db, item.code)
        if position.qty > 0 or position.value != 0:
            ledger_total = money(ledger_total + position.value)

    inventory_variance = money(gl_inventory - ledger_total)

    checks = [
        IntegrityCheck(
            name="Journal entries balance (debits = credits)",
            passed=tb.total_debit == tb.total_credit,
            detail=f"Debits {tb.total_debit} vs credits {tb.total_credit}",
            value=tb.difference,
        ),
        IntegrityCheck(
            name="Trial balance nets to zero",
            passed=tb.balanced,
            detail=f"Difference {tb.difference}",
            value=tb.difference,
        ),
        IntegrityCheck(
            name="Balance sheet balances (Assets = Liabilities + Equity)",
            passed=bs.is_balanced,
            detail=f"Check value {bs.check}",
            value=bs.check,
        ),
        IntegrityCheck(
            name="General Ledger inventory equals stock ledger value",
            passed=inventory_variance == 0,
            detail=(
                f"GL inventory {gl_inventory} vs stock ledger {ledger_total} "
                f"(variance {inventory_variance})"
            ),
            value=inventory_variance,
        ),
    ]
    return IntegrityReport(
        checks=checks, all_passed=all(check.passed for check in checks)
    )
