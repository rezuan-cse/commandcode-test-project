#!/usr/bin/env python3
"""Generate 1-2 years of realistic demo activity for testing and review.

The system is hard to evaluate with a handful of vouchers: period reports,
P&L trends and inventory aging all need real volume across many months. This
script creates a small demo master (items, BOMs, parties, employees) and then
posts months of purchases, production runs, sales, receipts/payments and
payroll runs — all through the same service layer the UI uses, so every
voucher stays balanced and every stock movement is consistent.

Usage, from the repository root:

    # 18 months of demo data on the local database
    backend/.venv/bin/python scripts/generate_demo_data.py --months 18

    # Against the hosted production database (testing phase only):
    RPCI_DATABASE_URL="postgresql+psycopg://..." \
        backend/.venv/bin/python scripts/generate_demo_data.py --months 24

Safety:

* The script refuses to run when the database already holds journal entries,
  unless ``--force`` is passed. On a completely empty database it seeds the
  starter chart of accounts itself; otherwise wipe first from
  Administration -> Data ("Empty everything"), or pass ``--wipe-first``
  to empty the books (fresh starter chart) and generate in one step.
  Sign-in accounts are never touched by a wipe.
* Everything is deterministic for a given ``--seed``: the same seed and month
  count always produce the same data, so a test run is reproducible.
* Demo master records use a ``DEMO-`` prefix where codes allow it, and every
  posting is recorded with ``posted_by="demo-generator"``.
* Before go-live, wipe the demo data from Administration -> Data. This script
  is for the testing phase only.

Design of the demo business (a small resin operation):

* Raw materials RM-201/202/203 and packaging PKG-201 are purchased.
* Finished goods FG-201/FG-202 are produced from a BOM, then sold.
* Each month: purchases first (with a buffer so production never starves),
  then production runs, then sales of most of what was produced, then a few
  receipts/payments against the invoices, then the monthly payroll run.
* Volumes grow gently month over month with noise, so trend reports have
  something to show.
"""

from __future__ import annotations

import argparse
import calendar
import random
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import func, select  # noqa: E402

from app.core.db import SessionLocal, init_db  # noqa: E402
from app.modules.accounts.models import Account  # noqa: E402
from app.seed.starter import seed_starter  # noqa: E402
from app.core.enums import (  # noqa: E402
    ItemCategory,
    PartyKind,
    PaymentDirection,
    Segment,
)
from app.modules.items_bom import service as items_svc  # noqa: E402
from app.modules.items_bom.models import BomComponent  # noqa: E402
from app.modules.items_bom.repository import add_components  # noqa: E402
from app.modules.items_bom.schemas import ItemIn  # noqa: E402
from app.modules.data import service as data_svc  # noqa: E402
from app.modules.journal_entries import service as journal_svc  # noqa: E402
from app.modules.parties import service as parties_svc  # noqa: E402
from app.modules.parties.schemas import PartyIn  # noqa: E402
from app.modules.payments import service as payments_svc  # noqa: E402
from app.modules.payments.schemas import PaymentIn  # noqa: E402
from app.modules.payroll import service as payroll_svc  # noqa: E402
from app.modules.payroll.schemas import EmployeeIn, PayrollRequest  # noqa: E402
from app.modules.production import service as production_svc  # noqa: E402
from app.modules.production.schemas import ProductionRequest  # noqa: E402
from app.modules.purchases import service as purchases_svc  # noqa: E402
from app.modules.purchases.schemas import PurchaseLineIn, PurchaseRequest  # noqa: E402
from app.modules.reports import service as reports_svc  # noqa: E402
from app.modules.sales import service as sales_svc  # noqa: E402
from app.modules.sales.schemas import SaleLineIn, SaleRequest  # noqa: E402

POSTED_BY = "demo-generator"
MONEY_ACCOUNT = "1010"  # Cash and Bank, from the starter chart of accounts

# (code, name, category, segment, uom)
ITEMS: list[tuple[str, str, ItemCategory, Segment, str]] = [
    ("RM-201", "Demo Resin Grade A", ItemCategory.RAW_MATERIAL, Segment.MANUFACTURING, "kg"),
    ("RM-202", "Demo Resin Grade B", ItemCategory.RAW_MATERIAL, Segment.MANUFACTURING, "kg"),
    ("RM-203", "Demo Additive X", ItemCategory.RAW_MATERIAL, Segment.MANUFACTURING, "kg"),
    ("PKG-201", "Demo Carton Box", ItemCategory.PACKAGING, Segment.PACKAGING, "pcs"),
    ("FG-201", "Demo Finished Resin 25kg", ItemCategory.FINISHED_GOOD, Segment.MANUFACTURING, "bag"),
    ("FG-202", "Demo Finished Resin 50kg", ItemCategory.FINISHED_GOOD, Segment.MANUFACTURING, "bag"),
]

# Finished good -> [(component code, qty per finished unit)]
BOMS: dict[str, list[tuple[str, Decimal]]] = {
    "FG-201": [("RM-201", Decimal("22")), ("RM-203", Decimal("2")), ("PKG-201", Decimal("1"))],
    "FG-202": [("RM-202", Decimal("45")), ("RM-203", Decimal("3")), ("PKG-201", Decimal("1"))],
}

# Base unit costs, drifted gently upward over time.
BASE_COSTS: dict[str, Decimal] = {
    "RM-201": Decimal("32"),
    "RM-202": Decimal("30"),
    "RM-203": Decimal("85"),
    "PKG-201": Decimal("45"),
}

# Sale prices per finished unit. Set for a healthy gross margin: finished-unit
# cost runs ~940 (FG-201) / ~1710 (FG-202), and monthly payroll is ~151k, so
# prices need headroom above both.
SALE_PRICES: dict[str, Decimal] = {
    "FG-201": Decimal("1350"),
    "FG-202": Decimal("2600"),
}

SUPPLIERS = [
    ("SUP-01", "Demo Supplier Ltd"),
    ("SUP-02", "Demo Polymers Trading"),
]

CUSTOMERS = [
    ("CUS-01", "Demo Builders Ltd"),
    ("CUS-02", "Demo Plastics Works"),
    ("CUS-03", "Demo Retail Traders"),
]

# (code, name, designation, department, gross monthly salary)
EMPLOYEES = [
    ("EMP-01", "Demo Manager", "General Manager", "office", Decimal("60000")),
    ("EMP-02", "Demo Accountant", "Accounts Officer", "office", Decimal("35000")),
    ("EMP-03", "Demo Operator A", "Machine Operator", "factory", Decimal("28000")),
    ("EMP-04", "Demo Operator B", "Machine Operator", "factory", Decimal("28000")),
]


def _money(value: float) -> Decimal:
    return Decimal(str(round(value, 2)))


def ensure_master(db, rng: random.Random) -> None:
    """Create the demo master data, skipping anything that already exists."""
    for code, name, category, segment, uom in ITEMS:
        try:
            items_svc.get_item(db, code)
            continue
        except items_svc.NotFoundError:
            pass
        items_svc.create_item(
                db,
                ItemIn(
                    code=code,
                    name=name,
                    category=category,
                    segment=segment,
                    uom=uom,
                    reorder_level=Decimal("100"),
                ),
            )
    for parent, components in BOMS.items():
        existing = {c.component_code for c in items_svc.list_components(db, parent)}
        missing = [
            BomComponent(parent_code=parent, component_code=code, qty_per_unit=qty)
            for code, qty in components
            if code not in existing
        ]
        if missing:
            add_components(db, missing)
    for code, name in SUPPLIERS:
        try:
            parties_svc.get_party(db, code)
        except parties_svc.NotFoundError:
            parties_svc.create_party(
                db,
                PartyIn(code=code, name=name, kind=PartyKind.SUPPLIER, credit_days=30),
            )
    for code, name in CUSTOMERS:
        try:
            parties_svc.get_party(db, code)
        except parties_svc.NotFoundError:
            parties_svc.create_party(
                db,
                PartyIn(code=code, name=name, kind=PartyKind.CUSTOMER, credit_days=30),
            )
    existing_employees = {e.code for e in payroll_svc.list_employees(db)}
    for code, name, designation, department, salary in EMPLOYEES:
        if code not in existing_employees:
            payroll_svc.create_employee(
                db,
                EmployeeIn(
                    code=code,
                    name=name,
                    designation=designation,
                    department=department,  # type: ignore[arg-type]
                    joining_date=date(2024, 1, 1),
                    gross_salary=salary,
                ),
            )
    db.commit()


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _day(rng: random.Random, year: int, month: int, lo: int, hi: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(max(rng.randint(lo, hi), 1), last_day))


def generate_month(
    db,
    rng: random.Random,
    year: int,
    month: int,
    month_index: int,
    counts: dict[str, int],
) -> None:
    """Post one month of demo activity: buy, make, sell, collect/pay, payroll."""
    # Gentle growth over time with noise, so trend reports have shape.
    growth = 1.0 + 0.025 * month_index
    noise = lambda base, pct=0.25: base * (1 + rng.uniform(-pct, pct))  # noqa: E731

    # --- Purchases (early in the month) -------------------------------------
    # Buy enough raw material for this month's planned production plus buffer,
    # so production runs never starve.
    planned_fg = {
        "FG-201": int(noise(220 * growth, 0.2)),
        "FG-202": int(noise(140 * growth, 0.2)),
    }
    rm_need: dict[str, Decimal] = {}
    for fg, qty in planned_fg.items():
        for comp_code, per_unit in BOMS[fg]:
            rm_need[comp_code] = rm_need.get(comp_code, Decimal("0")) + per_unit * qty
    for rm_code, need in rm_need.items():
        buy_qty = int(need * Decimal("1.5"))
        if buy_qty <= 0:
            continue
        unit_cost = _money(float(BASE_COSTS[rm_code]) * (1 + 0.004 * month_index) * (1 + rng.uniform(-0.05, 0.05)))
        supplier = rng.choice(SUPPLIERS)[0]
        # Split large buys into two lots for realism.
        lots = [buy_qty] if buy_qty < 4000 or rng.random() < 0.5 else [buy_qty // 2, buy_qty - buy_qty // 2]
        for lot in lots:
            purchases_svc.post(
                db,
                PurchaseRequest(
                    supplier=f"Demo purchase ({supplier})",
                    party_code=supplier,
                    purchase_date=_day(rng, year, month, 2, 8),
                    lines=[PurchaseLineIn(item_code=rm_code, qty=Decimal(lot), unit_cost=unit_cost)],
                ),
                posted_by=POSTED_BY,
            )
            counts["purchases"] += 1

    # --- Production runs (mid-month) -----------------------------------------
    produced: dict[str, int] = {}
    for fg, qty in planned_fg.items():
        if qty <= 0:
            continue
        # Even split across runs of ~120 units; components resolve from the
        # BOM automatically (lines=None).
        per_run = max(1, qty // max(1, qty // 120))
        made = 0
        while made < qty:
            run_qty = min(per_run, qty - made)
            production_svc.post(
                db,
                ProductionRequest(
                    output_item_code=fg,
                    qty_produced=Decimal(run_qty),
                    production_date=_day(rng, year, month, 10, 18),
                    labor_cost=_money(rng.uniform(1500, 3500)),
                    overhead_cost=_money(rng.uniform(800, 2000)),
                ),
                posted_by=POSTED_BY,
            )
            counts["production_runs"] += 1
            made += run_qty
        produced[fg] = qty

    # --- Sales (through the month, only what was produced) --------------------
    for fg, qty in produced.items():
        sell_total = int(qty * rng.uniform(0.6, 0.9))
        n_sales = rng.randint(3, 5)
        remaining = sell_total
        for i in range(n_sales):
            if remaining <= 0:
                break
            line_qty = remaining if i == n_sales - 1 else max(1, remaining // (n_sales - i))
            remaining -= line_qty
            customer = rng.choice(CUSTOMERS)[0]
            price = _money(float(SALE_PRICES[fg]) * (1 + rng.uniform(-0.04, 0.06)))
            sales_svc.post(
                db,
                SaleRequest(
                    customer=f"Demo sale ({customer})",
                    party_code=customer,
                    sale_date=_day(rng, year, month, 12, 26),
                    lines=[SaleLineIn(item_code=fg, qty=Decimal(line_qty), sale_price=price)],
                ),
                posted_by=POSTED_BY,
            )
            counts["sales"] += 1
            # Settle about half the invoices a few days later.
            if rng.random() < 0.5:
                payments_svc.post(
                    db,
                    PaymentIn(
                        direction=PaymentDirection.RECEIPT,
                        party_code=customer,
                        pay_date=_day(rng, year, month, 15, 28),
                        amount=_money(float(Decimal(line_qty) * price)),
                        money_account=MONEY_ACCOUNT,
                        reference="Demo receipt",
                    ),
                    posted_by=POSTED_BY,
                )
                counts["receipts"] += 1

    # --- Supplier payments (a few per month, money on account) -----------------
    for _ in range(rng.randint(1, 3)):
        supplier = rng.choice(SUPPLIERS)[0]
        payments_svc.post(
            db,
            PaymentIn(
                direction=PaymentDirection.PAYMENT,
                party_code=supplier,
                pay_date=_day(rng, year, month, 15, 28),
                amount=_money(rng.uniform(20000, 90000)),
                money_account=MONEY_ACCOUNT,
                reference="Demo supplier payment",
            ),
            posted_by=POSTED_BY,
        )
        counts["payments"] += 1

    # --- Payroll run (end of month) --------------------------------------------
    first, last = _month_bounds(year, month)
    payroll_svc.post_run(
        db,
        PayrollRequest(period_start=first, period_end=last, pay_date=last),
        posted_by=POSTED_BY,
    )
    counts["payroll_runs"] += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--months",
        type=int,
        default=18,
        help="how many months of activity to generate (default: 18)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="random seed; same seed + months = same data (default: 42)",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="last month as YYYY-MM (default: the current month)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="run even if the database already holds journal entries",
    )
    parser.add_argument(
        "--wipe-first",
        action="store_true",
        help="empty the books (fresh starter chart of accounts) before "
        "generating, in one step. Sign-in accounts are kept. This is the "
        "scripted equivalent of Administration -> Data -> 'Empty everything'.",
    )
    args = parser.parse_args()

    if args.months < 1 or args.months > 60:
        raise SystemExit("--months must be between 1 and 60.")

    if args.end:
        end_year, end_month = (int(p) for p in args.end.split("-"))
        end = date(end_year, end_month, 1)
    else:
        today = date.today()
        end = date(today.year, today.month, 1)
    # Walk back to the first month (inclusive).
    start_year, start_month = end.year, end.month
    for _ in range(args.months - 1):
        start_month -= 1
        if start_month == 0:
            start_month, start_year = 12, start_year - 1

    init_db()
    if args.wipe_first:
        report = data_svc.reset("fresh")
        print(f"Wiped the books: {report.summary()}")
    db = SessionLocal()
    try:
        existing = journal_svc.list_entries(db, limit=1)
        if existing and not args.force:
            raise SystemExit(
                "The database already holds journal entries. Refusing to mix demo "
                "data into real books.\nWipe first from Administration -> Data "
                "(\"Empty everything\"), or re-run with --force if you really "
                "mean it."
            )

        # An empty database has no chart of accounts yet; the postings below
        # need the starter chart. Idempotent — a no-op when accounts exist.
        if db.execute(select(func.count()).select_from(Account)).scalar_one() == 0:
            added = seed_starter(db)
            print(f"Seeded the starter chart of accounts ({added} accounts).")

        rng = random.Random(args.seed)
        ensure_master(db, rng)

        counts = {
            "purchases": 0,
            "production_runs": 0,
            "sales": 0,
            "receipts": 0,
            "payments": 0,
            "payroll_runs": 0,
        }
        y, m, index = start_year, start_month, 0
        while (y, m) <= (end.year, end.month):
            generate_month(db, rng, y, m, index, counts)
            index += 1
            m += 1
            if m == 13:
                m, y = 1, y + 1

        # Final integrity check: the books must still balance.
        tb = reports_svc.trial_balance(db, date.today())
        print(f"Generated {args.months} months of demo activity "
              f"({start_year}-{start_month:02d} .. {end.year}-{end.month:02d}):")
        for key, value in counts.items():
            print(f"  {key:16s} {value}")
        print(f"Trial balance difference: {tb.difference} "
              f"(must be 0 — the books balance)")
        if tb.difference != 0:
            raise SystemExit("ERROR: trial balance does not net to zero!")
        print("Done. Wipe it any time from Administration -> Data before go-live.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
