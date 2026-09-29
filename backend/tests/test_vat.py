"""VAT on sales and purchases, driven by the settings table.

With VAT switched off — the default until the client confirms the rules — the
books behave exactly as before. These tests turn it on and off again to check the
tax is computed, posted, reported and reversed, and that nothing is hardcoded.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.modules.inventory_ledger import service as ledger
from app.modules.journal_entries import repository as journal_repo
from app.modules.purchases import service as purchases
from app.modules.purchases.schemas import PurchaseLineIn, PurchaseRequest
from app.modules.reports import service as reports
from app.modules.sales import service as sales
from app.modules.sales.schemas import SaleLineIn, SaleRequest
from app.modules.settings import service as settings_service
from app.modules.settings.schemas import SettingUpdate
from app.modules.vat_tax import service as vat

POSTING_DATE = date(2026, 10, 12)


def _set(db, key: str, value: str) -> None:
    """Write a configuration value the way the Configuration screen would."""
    settings_service.seed_defaults(db)
    settings_service.update_setting(db, key, SettingUpdate(value=value))


def _enable_vat(db, *, inclusive: bool = False, rate: str = "15") -> None:
    _set(db, "vat.charge_vat", "true")
    _set(db, "vat.standard_rate_pct", rate)
    _set(db, "vat.prices_include_vat", "true" if inclusive else "false")


def _receive_stock(db, qty: str = "10", cost: str = "1000"):
    return purchases.post(
        db,
        PurchaseRequest(
            supplier="Test Supplier",
            purchase_date=POSTING_DATE,
            lines=[PurchaseLineIn(item_code="TRD001", qty=Decimal(qty), unit_cost=Decimal(cost))],
        ),
    )


def _sell(db, qty: str = "4", price: str = "1500"):
    return sales.post(
        db,
        SaleRequest(
            customer="Test Customer",
            sale_date=POSTING_DATE,
            lines=[SaleLineIn(item_code="TRD001", qty=Decimal(qty), sale_price=Decimal(price))],
        ),
    )


def _has_line(entry, account: str) -> Decimal:
    """The net credit on an account within one entry."""
    debit = sum((line.debit for line in entry.lines if line.account_code == account), Decimal("0"))
    credit = sum((line.credit for line in entry.lines if line.account_code == account), Decimal("0"))
    return Decimal(credit) - Decimal(debit)


def test_vat_is_off_by_default(db) -> None:
    """Without confirmation, a sale carries no tax."""
    _receive_stock(db)
    result = _sell(db)
    assert result.order.vat_total == 0
    assert result.preview.vat_total == 0
    assert result.preview.grand_total == result.preview.revenue == 6000


def test_output_vat_is_added_on_top(db) -> None:
    """Exclusive prices: VAT is added and the receivable carries the gross."""
    _receive_stock(db)
    _enable_vat(db)
    result = _sell(db)

    assert result.preview.revenue == 6000
    assert result.preview.vat_total == 900
    assert result.preview.grand_total == 6900
    assert result.order.vat_total == 900

    entry = journal_repo.get_entry(db, result.order.journal_entry_id)
    assert _has_line(entry, vat.output_account(db)) == 900
    assert (
        sum(line.debit for line in entry.lines) == sum(line.credit for line in entry.lines)
    )
    assert reports.trial_balance(db, POSTING_DATE).difference == 0


def test_inclusive_prices_have_vat_backed_out(db) -> None:
    """Inclusive prices: the tax is taken out of the line, not added to it."""
    _receive_stock(db)
    _enable_vat(db, inclusive=True)
    result = _sell(db)

    # 6,000 inclusive of 15% is 5,217.3913 net plus 782.6087 tax.
    assert result.preview.revenue == Decimal("5217.3913")
    assert result.preview.vat_total == Decimal("782.6087")
    assert result.preview.grand_total == 6000


def test_input_vat_is_recoverable_on_purchases(db) -> None:
    """A purchase debits input VAT and credits the payable gross."""
    _enable_vat(db)
    result = _receive_stock(db)

    assert result.preview.total_value == 10000
    assert result.preview.vat_total == 1500
    entry = journal_repo.get_entry(db, result.order.journal_entry_id)
    assert _has_line(entry, vat.input_account(db)) == -1500  # a debit
    # Inventory is still carried at the net cost, not the gross.
    assert ledger.position(db, "TRD001").avg_cost == 1000


def test_a_zero_rated_item_carries_no_vat(db) -> None:
    """An exempt item is listed in the settings and carries no tax."""
    _receive_stock(db)
    _enable_vat(db)
    _set(db, "vat.zero_rated_items", '["TRD001"]')
    result = _sell(db)
    assert result.preview.vat_total == 0


def test_vat_can_be_limited_to_some_segments(db) -> None:
    """A segment outside the configured list is not taxed."""
    _receive_stock(db)
    _enable_vat(db)
    _set(db, "vat.applies_to_segments", '["Manufacturing"]')
    result = _sell(db)  # TRD001 is a Trading item
    assert result.preview.vat_total == 0


def test_the_vat_summary_nets_output_against_input(db) -> None:
    """The report subtracts recoverable input VAT from output VAT."""
    _enable_vat(db)
    _receive_stock(db)  # input VAT 1,500
    _sell(db)  # output VAT 900

    totals = vat.summary(db, date(2026, 1, 1), POSTING_DATE)
    assert totals["output_vat"] == 900
    assert totals["input_vat"] == 1500
    assert totals["net_payable"] == -600


def test_reversing_a_sale_unwinds_its_vat(db) -> None:
    """The mirror entry carries the VAT line away with everything else."""
    _receive_stock(db)
    _enable_vat(db)
    result = _sell(db)

    sales.reverse(
        db, result.order.id, reason="Wrong customer", posted_by="tester"
    )
    db.expire_all()
    assert vat.summary(db, date(2026, 1, 1), POSTING_DATE)["output_vat"] == 0
    assert reports.trial_balance(db, POSTING_DATE).difference == 0
