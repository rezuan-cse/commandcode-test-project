#!/usr/bin/env python3
"""Build a small sample workbook for testing the system end to end.

The workbook has the same sheet names and column layout the importer expects, so
it can be loaded from Administration → Data and used to walk through a purchase,
a production run and a sale with figures that are easy to check by hand.

Usage, from the repository root:

    backend/.venv/bin/python scripts/make_sample_workbook.py

Writes SAMPLE_TEST_WORKBOOK.xlsx next to this repository's root.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from openpyxl import Workbook

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "SAMPLE_TEST_WORKBOOK.xlsx"

CUTOVER = dt.date(2026, 1, 1)

# (code, name, type, segment, normal balance)
ACCOUNTS = [
    ("1010", "Cash and Bank", "Asset", "Shared", "Dr"),
    ("1100", "Accounts Receivable", "Asset", "Shared", "Dr"),
    ("1130", "VAT Current Account", "Asset", "Shared", "Dr"),
    ("1200", "Imported Goods Inventory", "Asset", "Import", "Dr"),
    ("1210", "Raw Material Inventory", "Asset", "Manufacturing", "Dr"),
    ("1220", "Work in Progress", "Asset", "Manufacturing", "Dr"),
    ("1230", "Finished Goods Inventory", "Asset", "Manufacturing", "Dr"),
    ("1240", "Packaging Inventory", "Asset", "Packaging", "Dr"),
    ("1250", "Trading Stock", "Asset", "Trading", "Dr"),
    ("2000", "Accounts Payable — Import", "Liability", "Import", "Cr"),
    ("2010", "Accounts Payable — Local", "Liability", "Shared", "Cr"),
    ("2200", "VAT Payable", "Liability", "Shared", "Cr"),
    ("2210", "TDS Payable", "Liability", "Shared", "Cr"),
    ("2220", "AIT Payable", "Liability", "Shared", "Cr"),
    ("3000", "Share Capital", "Equity", "Shared", "Cr"),
    ("3100", "Retained Earnings", "Equity", "Shared", "Cr"),
    ("4000", "Sales — Import", "Revenue", "Import", "Cr"),
    ("4010", "Sales — Manufacturing", "Revenue", "Manufacturing", "Cr"),
    ("4020", "Sales — Packaging", "Revenue", "Packaging", "Cr"),
    ("4030", "Sales — Trading", "Revenue", "Trading", "Cr"),
    ("4040", "Sales — Application", "Revenue", "Application", "Cr"),
    ("5000", "COGS — Import", "COGS", "Import", "Dr"),
    ("5010", "COGS — Manufacturing", "COGS", "Manufacturing", "Dr"),
    ("5020", "COGS — Packaging", "COGS", "Packaging", "Dr"),
    ("5030", "COGS — Trading", "COGS", "Trading", "Dr"),
    ("5011", "Factory Labour", "Expense", "Manufacturing", "Dr"),
    ("6000", "Operating Expenses", "Expense", "Shared", "Dr"),
    ("6010", "Office Salaries", "Expense", "Shared", "Dr"),
    ("6200", "Sales Commission", "Expense", "Shared", "Dr"),
]

# (account code, name, debit, credit)
OPENING_BALANCES = [
    ("1010", "Cash and Bank", 494000, 0),
    ("1210", "Raw Material Inventory", 3500, 0),
    ("1240", "Packaging Inventory", 500, 0),
    ("1250", "Trading Stock", 2000, 0),
    ("3000", "Share Capital", 0, 500000),
]

# (code, name, category, segment, unit of measure)
ITEMS = [
    ("RM-100", "Raw Material A", "Raw Material", "Manufacturing", "kg"),
    ("RM-200", "Raw Material B", "Raw Material", "Manufacturing", "kg"),
    ("PKG-100", "Packaging Box", "Packaging", "Packaging", "Pcs"),
    ("FG-100", "Finished Good X", "Finished Good", "Manufacturing", "Pcs"),
    ("TRD-100", "Trading Item", "Trading Stock", "Trading", "Pcs"),
]

# (parent, stage, component, quantity per unit)
BOM = [
    ("FG-100", 1, "RM-100", 2),  # 2 kg of RM-100 per unit of FG-100
    ("FG-100", 1, "RM-200", 1),  # 1 kg of RM-200 per unit of FG-100
    ("FG-100", 1, "PKG-100", 1),  # 1 box per unit of FG-100
]

# (date, item, type, reference, in qty, in value)
OPENING_STOCK = [
    (CUTOVER, "RM-100", "Opening Stock", "OPEN-001", 100, 2000),
    (CUTOVER, "RM-200", "Opening Stock", "OPEN-002", 50, 1500),
    (CUTOVER, "PKG-100", "Opening Stock", "OPEN-003", 100, 500),
    (CUTOVER, "TRD-100", "Opening Stock", "OPEN-004", 20, 2000),
]


def build() -> Path:
    """Write the sample workbook and return its path."""
    wb = Workbook()

    accounts = wb.active
    accounts.title = "Chart of Accounts"
    accounts.append(["Code", "Account name", "Type", "Segment", "Normal balance"])
    for row in ACCOUNTS:
        accounts.append(list(row))

    opening = wb.create_sheet("Opening Balances")
    opening.append(["Cutover date", CUTOVER])
    opening.append(["Code", "Account name", "Debit", "Credit"])
    for row in OPENING_BALANCES:
        opening.append(list(row))

    journal = wb.create_sheet("Journal Entries")
    journal.append(
        ["Date", "Date", "Voucher", "Account code", "Account name", "Segment",
         "Debit", "Credit", "Narration", "Posted by"]
    )
    # No historical journal entries: this sample starts clean with opening
    # balances and opening stock only.

    items = wb.create_sheet("Item Master")
    items.append(["Code", "Name", "Category", "Segment", "Unit"])
    for row in ITEMS:
        items.append(list(row))

    bom = wb.create_sheet("BOM Master")
    bom.append(["Parent", "Parent name", "Stage", "Component", "Component name",
                "Qty per unit"])
    for parent, stage, component, qty in BOM:
        bom.append([parent, "", stage, component, "", qty])

    ledger = wb.create_sheet("Inventory Ledger")
    ledger.append(
        ["Date", "Item", "Item name", "Type", "Reference", "In qty", "In value",
         "Out qty", "Out value", "Suggested out value", "", "", "Avg cost"]
    )
    for when, item, kind, reference, in_qty, in_value in OPENING_STOCK:
        ledger.append([when, item, "", kind, reference, in_qty, in_value, 0, 0, 0])

    wb.save(str(OUTPUT))
    return OUTPUT


def main() -> int:
    path = build()
    print(f"Wrote {path}")
    print(
        f"  {len(ACCOUNTS)} accounts, {len(ITEMS)} items, {len(BOM)} BOM lines, "
        f"{len(OPENING_BALANCES)} opening balances, {len(OPENING_STOCK)} opening stock rows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
