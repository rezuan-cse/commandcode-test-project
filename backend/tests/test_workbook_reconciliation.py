"""Proves the seeded database reproduces the client's own workbook figures.

These are the acceptance numbers from the build plan: the demo is only credible
if opening the reports shows exactly what the client sees in their spreadsheet.
"""

from __future__ import annotations

from datetime import date

from app.modules.inventory_ledger import service as ledger
from app.modules.reports import repository as reports_repo
from app.modules.reports import service as reports

AS_OF = date(2026, 10, 31)
PERIOD_START = date(2026, 1, 1)


def test_chart_of_accounts_imported(db) -> None:
    """All 89 accounts from the workbook are present."""
    accounts = reports_repo.all_accounts(db)
    assert len(accounts) == 89
    assert accounts[0].code == "1000"


def test_trial_balance_nets_to_zero(db) -> None:
    """Trial balance debits equal credits, to the penny."""
    tb = reports.trial_balance(db, AS_OF)
    assert tb.total_debit == tb.total_credit
    assert tb.difference == 0
    assert tb.balanced is True


def test_balance_sheet_balances_at_801600(db) -> None:
    """Assets equal liabilities plus equity, at the workbook's 801,600."""
    bs = reports.balance_sheet(db, AS_OF)
    assert bs.total_assets == 801600
    assert bs.total_liabilities == 0
    assert bs.total_equity == 801600
    assert bs.check == 0
    assert bs.is_balanced is True


def test_segment_pnl_matches_workbook(db) -> None:
    """Manufacturing shows 4,000 revenue, 2,400 COGS, 40% margin."""
    pnl = reports.pnl_by_segment(db, PERIOD_START, AS_OF)
    manufacturing = next(row for row in pnl.segments if row.segment == "Manufacturing")
    assert manufacturing.revenue == 4000
    assert manufacturing.cogs == 2400
    assert manufacturing.gross_profit == 1600
    assert manufacturing.gross_margin_pct == 40
    assert pnl.net_profit == 1600


def test_rmc003_average_cost_matches_workbook(db) -> None:
    """Elephent Cement keeps the workbook's 790 kg at 32.27848101."""
    position = ledger.position(db, "RMC-003")
    assert position.qty == 790
    assert position.value == 25500
    assert str(position.avg_cost) == "32.27848101"


def test_historical_out_value_preserved(db) -> None:
    """The imported production issue keeps the value the client recorded.

    The workbook recorded 7,000 for 210 kg that its own suggested-value column
    priced at 6,825. The import preserves the recorded figure so the stock
    ledger matches their sheet, and the difference stays visible.
    """
    rows = ledger.list_rows(db, item_code="RMC-003")
    issue = next(row for row in rows if row.out_qty == 210)
    assert issue.out_value == 7000
    assert issue.out_value != 210 * issue.avg_cost


def test_inventory_integrity_check_flags_workbook_variance(db) -> None:
    """The GL-versus-stock-ledger check surfaces the client's real variance.

    The workbook's memo ledger holds 775,500 of stock while the general ledger
    carries 301,400, because the memo sheet never posts journals. The check must
    flag this rather than silently agree.
    """
    report = reports.integrity_report(db, AS_OF)
    inventory_check = next(
        check for check in report.checks if check.name.startswith("General Ledger inventory")
    )
    assert inventory_check.passed is False
    assert inventory_check.value == -474100


def test_first_three_checks_pass(db) -> None:
    """Everything the system itself controls is provably balanced."""
    report = reports.integrity_report(db, AS_OF)
    controllable = [check for check in report.checks[:3]]
    assert all(check.passed for check in controllable)
