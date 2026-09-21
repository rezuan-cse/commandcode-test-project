#!/usr/bin/env python3
"""Load (or reload) the demo database from the client's workbook.

Usage, from the repository root:

    backend/.venv/bin/python scripts/seed_from_excel.py            # seed if empty
    backend/.venv/bin/python scripts/seed_from_excel.py --rebuild  # wipe and reseed
    backend/.venv/bin/python scripts/seed_from_excel.py --check    # verify, change nothing

The ``--check`` mode prints the reconciliation figures the demo must reproduce
so a regression in the import is caught before showing the client.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.db import Base, SessionLocal, engine, init_db  # noqa: E402
from app.modules.inventory_ledger import service as ledger  # noqa: E402
from app.modules.reports import service as reports  # noqa: E402
from app.seed.loader import seed_if_empty  # noqa: E402

AS_OF = date(2026, 10, 31)
PERIOD_FROM = date(2026, 1, 1)


def rebuild() -> None:
    """Drop every table and recreate the schema."""
    from app import models_registry  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Dropped and recreated the schema.")


def report(session) -> None:
    """Print the figures the demo is expected to reproduce."""
    tb = reports.trial_balance(session, AS_OF)
    bs = reports.balance_sheet(session, AS_OF)
    pnl = reports.pnl_by_segment(session, PERIOD_FROM, AS_OF)
    integrity = reports.integrity_report(session, AS_OF)
    cement = ledger.position(session, "RMC-003")

    print("\nReconciliation against the workbook")
    print("-" * 58)
    print(f"  Trial balance difference      {tb.difference}   (expect 0)")
    print(f"  Total assets                  {bs.total_assets}   (expect 801600)")
    print(f"  Balance sheet check           {bs.check}   (expect 0)")
    print(f"  Net profit                    {pnl.net_profit}   (expect 1600)")
    print(f"  RMC-003 quantity              {cement.qty}   (expect 790)")
    print(f"  RMC-003 average cost          {cement.avg_cost}   (expect 32.27848101)")
    print("\nIntegrity checks")
    print("-" * 58)
    for check in integrity.checks:
        mark = "PASS" if check.passed else "FLAG"
        print(f"  [{mark}] {check.name}")
        print(f"         {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true", help="wipe the database first")
    parser.add_argument("--check", action="store_true", help="only print reconciliation figures")
    args = parser.parse_args()

    if args.rebuild and not args.check:
        rebuild()
    elif not args.check:
        init_db()

    with SessionLocal() as session:
        if not args.check:
            result = seed_if_empty(session)
            if result.seeded:
                print(f"Seeded: {result.counts}")
            else:
                print("Database already contains accounts; nothing imported.")
            for warning in result.warnings:
                print(f"Warning: {warning}")
        report(session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
