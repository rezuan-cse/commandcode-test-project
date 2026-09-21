"""Account mappings used by the automatic journal-entry generators.

These mirror the account codes in the client's workbook exactly, so
auto-generated entries look identical to the ones they already write by hand.
"""

from __future__ import annotations

from app.core.enums import ItemCategory, Segment

# Inventory asset account per item category.
INVENTORY_ACCOUNT_BY_CATEGORY: dict[ItemCategory, str] = {
    ItemCategory.IMPORTED_GOODS: "1200",
    ItemCategory.RAW_MATERIAL: "1210",
    ItemCategory.WIP: "1220",
    ItemCategory.FINISHED_GOOD: "1230",
    ItemCategory.PACKAGING: "1240",
    ItemCategory.TRADING: "1250",
}

# Revenue account per reporting segment.
SALES_ACCOUNT_BY_SEGMENT: dict[Segment, str] = {
    Segment.IMPORT: "4000",
    Segment.MANUFACTURING: "4010",
    Segment.PACKAGING: "4020",
    Segment.TRADING: "4030",
    Segment.APPLICATION: "4040",
    Segment.SHARED: "4010",
}

# Cost-of-goods-sold account per reporting segment.
COGS_ACCOUNT_BY_SEGMENT: dict[Segment, str] = {
    Segment.IMPORT: "5000",
    Segment.MANUFACTURING: "5010",
    Segment.PACKAGING: "5020",
    Segment.TRADING: "5030",
    Segment.APPLICATION: "5010",
    Segment.SHARED: "5010",
}

# Cash/bank account used to settle labor and overhead (matches the workbook).
DEFAULT_BANK_ACCOUNT = "1010"
# Receivable used for local credit sales.
DEFAULT_AR_ACCOUNT = "1100"
# Payables used when a purchase is not paid immediately.
DEFAULT_AP_LOCAL_ACCOUNT = "2010"
DEFAULT_AP_IMPORT_ACCOUNT = "2000"
# Where purchases of imported goods land when settled on credit.
IMPORT_PAYABLE_ACCOUNT = "2000"


def inventory_account(item_category: ItemCategory) -> str:
    """Return the inventory asset account for an item category."""
    return INVENTORY_ACCOUNT_BY_CATEGORY[item_category]


def sales_account(segment: Segment) -> str:
    """Return the revenue account for a segment."""
    return SALES_ACCOUNT_BY_SEGMENT[segment]


def cogs_account(segment: Segment) -> str:
    """Return the COGS account for a segment."""
    return COGS_ACCOUNT_BY_SEGMENT[segment]
