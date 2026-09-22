"""Domain enumerations shared across every module.

These mirror the workbook's terminology exactly so imported data maps 1:1.
"""

from __future__ import annotations

import enum


class AccountType(str, enum.Enum):
    """Chart-of-accounts classification."""

    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"
    REVENUE = "Revenue"
    COGS = "COGS"
    EXPENSE = "Expense"
    OTHER_INCOME = "Other Income"


class Segment(str, enum.Enum):
    """Business segment tag carried by every account, item, and journal line."""

    IMPORT = "Import"
    MANUFACTURING = "Manufacturing"
    PACKAGING = "Packaging"
    TRADING = "Trading"
    APPLICATION = "Application"
    SHARED = "Shared"


class NormalBalance(str, enum.Enum):
    """Which side increases the account."""

    DEBIT = "Dr"
    CREDIT = "Cr"


class ItemCategory(str, enum.Enum):
    """Item master classification."""

    RAW_MATERIAL = "Raw Material"
    WIP = "WIP"
    FINISHED_GOOD = "Finished Good"
    PACKAGING = "Packaging"
    TRADING = "Trading Stock"
    IMPORTED_GOODS = "Imported Goods"


class MovementType(str, enum.Enum):
    """Inventory ledger movement kinds."""

    OPENING = "Opening Stock"
    PURCHASE_IN = "Purchase-In"
    PRODUCTION_IN = "Production-In"
    PRODUCTION_OUT = "Production-Out"
    SALE_OUT = "Sale-Out"
    ADJUSTMENT = "Adjustment"
    # Stock moving back because a posted transaction was undone. Given their own
    # types rather than reusing the originals, so the ledger says plainly that a
    # row is a correction and not a fresh purchase or sale.
    REVERSAL_IN = "Reversal-In"
    REVERSAL_OUT = "Reversal-Out"


# Movement types that increase stock. Everything else decreases it.
INCREASING_MOVEMENTS = {
    MovementType.OPENING,
    MovementType.PURCHASE_IN,
    MovementType.PRODUCTION_IN,
    MovementType.REVERSAL_IN,
}


class JournalSource(str, enum.Enum):
    """What created a journal entry."""

    MANUAL = "Manual"
    PRODUCTION = "Production"
    SALES = "Sales"
    PURCHASE = "Purchase"
    PAYROLL = "Payroll"


class Role(str, enum.Enum):
    """System roles from the build spec, section 4."""

    ADMIN = "Admin"
    ACCOUNTANT = "Accountant"
    STORE_PRODUCTION = "Store/Production Staff"
    SALES_STAFF = "Sales Staff"
    OWNER_VIEWER = "Owner/Viewer"


# Accounts whose balance naturally increases on the debit side.
DEBIT_NATURED_TYPES = {
    AccountType.ASSET,
    AccountType.COGS,
    AccountType.EXPENSE,
}

# Accounts that reduce net profit when their debit balance grows.
PROFIT_AND_LOSS_TYPES = {
    AccountType.REVENUE,
    AccountType.COGS,
    AccountType.EXPENSE,
    AccountType.OTHER_INCOME,
}
