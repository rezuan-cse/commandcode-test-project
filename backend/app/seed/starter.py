"""A built-in starter chart of accounts.

A fresh deployment should be usable straight away: sign in, post a sale, and see a
trial balance that nets to zero. That needs a chart of accounts, so a standard one
is seeded at first boot — with zero balances and nothing else. The client's own
workbook can replace it at any time from Administration → Data.

The codes cover every account the automatic postings use, so sales, purchases,
production and payroll all have somewhere to post from day one, plus the accounts a
company starting from nothing needs to record its own affairs: a bank account,
machinery, loans and the usual expense heads. Nothing here is a balance — a new
company's figures arrive as journal entries it posts itself.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AccountType, NormalBalance, Segment
from app.modules.accounts.models import Account

# (code, name, type, segment, normal balance)
STARTER_ACCOUNTS: list[tuple[str, str, AccountType, Segment, NormalBalance]] = [
    # Assets
    ("1010", "Cash and Bank", AccountType.ASSET, Segment.SHARED, NormalBalance.DEBIT),
    ("1100", "Accounts Receivable", AccountType.ASSET, Segment.SHARED, NormalBalance.DEBIT),
    ("1130", "VAT Current Account", AccountType.ASSET, Segment.SHARED, NormalBalance.DEBIT),
    ("1200", "Imported Goods Inventory", AccountType.ASSET, Segment.IMPORT, NormalBalance.DEBIT),
    ("1210", "Raw Material Inventory", AccountType.ASSET, Segment.MANUFACTURING, NormalBalance.DEBIT),
    ("1220", "Work in Progress", AccountType.ASSET, Segment.MANUFACTURING, NormalBalance.DEBIT),
    ("1230", "Finished Goods Inventory", AccountType.ASSET, Segment.MANUFACTURING, NormalBalance.DEBIT),
    ("1240", "Packaging Inventory", AccountType.ASSET, Segment.PACKAGING, NormalBalance.DEBIT),
    ("1250", "Trading Stock", AccountType.ASSET, Segment.TRADING, NormalBalance.DEBIT),
    # Liabilities
    ("2000", "Accounts Payable — Import", AccountType.LIABILITY, Segment.IMPORT, NormalBalance.CREDIT),
    ("2010", "Accounts Payable — Local", AccountType.LIABILITY, Segment.SHARED, NormalBalance.CREDIT),
    ("2200", "VAT Payable", AccountType.LIABILITY, Segment.SHARED, NormalBalance.CREDIT),
    ("2210", "TDS Payable", AccountType.LIABILITY, Segment.SHARED, NormalBalance.CREDIT),
    ("2220", "AIT Payable", AccountType.LIABILITY, Segment.SHARED, NormalBalance.CREDIT),
    # Equity
    ("3000", "Share Capital", AccountType.EQUITY, Segment.SHARED, NormalBalance.CREDIT),
    ("3100", "Retained Earnings", AccountType.EQUITY, Segment.SHARED, NormalBalance.CREDIT),
    # Revenue
    ("4000", "Sales — Import", AccountType.REVENUE, Segment.IMPORT, NormalBalance.CREDIT),
    ("4010", "Sales — Manufacturing", AccountType.REVENUE, Segment.MANUFACTURING, NormalBalance.CREDIT),
    ("4020", "Sales — Packaging", AccountType.REVENUE, Segment.PACKAGING, NormalBalance.CREDIT),
    ("4030", "Sales — Trading", AccountType.REVENUE, Segment.TRADING, NormalBalance.CREDIT),
    ("4040", "Sales — Application", AccountType.REVENUE, Segment.APPLICATION, NormalBalance.CREDIT),
    # Cost of goods sold
    ("5000", "COGS — Import", AccountType.COGS, Segment.IMPORT, NormalBalance.DEBIT),
    ("5010", "COGS — Manufacturing", AccountType.COGS, Segment.MANUFACTURING, NormalBalance.DEBIT),
    ("5020", "COGS — Packaging", AccountType.COGS, Segment.PACKAGING, NormalBalance.DEBIT),
    ("5030", "COGS — Trading", AccountType.COGS, Segment.TRADING, NormalBalance.DEBIT),
    # Expenses
    ("5011", "Factory Labour", AccountType.EXPENSE, Segment.MANUFACTURING, NormalBalance.DEBIT),
    ("6000", "Operating Expenses", AccountType.EXPENSE, Segment.SHARED, NormalBalance.DEBIT),
    ("6010", "Office Salaries", AccountType.EXPENSE, Segment.SHARED, NormalBalance.DEBIT),
    ("6200", "Sales Commission", AccountType.EXPENSE, Segment.SHARED, NormalBalance.DEBIT),
    # --- What a going concern needs on top of the posting accounts ---------
    # A company starting from nothing has no balances but does have a bank
    # account, machinery, and rent to pay. Without these, every one of them would
    # be posted into "Operating Expenses" or "Cash and Bank" and the reports would
    # never separate them. None of these codes is used by an automatic posting, so
    # adding them cannot change how a sale or a run is costed.
    #
    # Assets
    ("1020", "Bank — Current Account", AccountType.ASSET, Segment.SHARED, NormalBalance.DEBIT),
    ("1030", "Bank — Short-Term Deposit", AccountType.ASSET, Segment.SHARED, NormalBalance.DEBIT),
    ("1300", "Advances and Deposits", AccountType.ASSET, Segment.SHARED, NormalBalance.DEBIT),
    ("1400", "Plant and Machinery", AccountType.ASSET, Segment.SHARED, NormalBalance.DEBIT),
    ("1410", "Accumulated Depreciation — Plant", AccountType.ASSET, Segment.SHARED, NormalBalance.CREDIT),
    ("1420", "Furniture and Fixtures", AccountType.ASSET, Segment.SHARED, NormalBalance.DEBIT),
    # Liabilities
    ("2110", "Loans", AccountType.LIABILITY, Segment.SHARED, NormalBalance.CREDIT),
    ("2300", "Accrued Expenses", AccountType.LIABILITY, Segment.SHARED, NormalBalance.CREDIT),
    ("2400", "Advances from Customers", AccountType.LIABILITY, Segment.SHARED, NormalBalance.CREDIT),
    ("2500", "Provision for Tax", AccountType.LIABILITY, Segment.SHARED, NormalBalance.CREDIT),
    # Equity
    ("3200", "Director's Loan", AccountType.EQUITY, Segment.SHARED, NormalBalance.CREDIT),
    # Expenses
    ("5100", "Depreciation", AccountType.EXPENSE, Segment.SHARED, NormalBalance.DEBIT),
    ("6100", "Rent", AccountType.EXPENSE, Segment.SHARED, NormalBalance.DEBIT),
    ("6110", "Utilities", AccountType.EXPENSE, Segment.SHARED, NormalBalance.DEBIT),
    ("6120", "Transport", AccountType.EXPENSE, Segment.SHARED, NormalBalance.DEBIT),
    ("6130", "Professional Fees", AccountType.EXPENSE, Segment.SHARED, NormalBalance.DEBIT),
    ("6140", "Repairs and Maintenance", AccountType.EXPENSE, Segment.SHARED, NormalBalance.DEBIT),
    ("6300", "Bank Charges", AccountType.EXPENSE, Segment.SHARED, NormalBalance.DEBIT),
    ("6400", "Marketing", AccountType.EXPENSE, Segment.SHARED, NormalBalance.DEBIT),
]


def seed_starter(db: Session) -> int:
    """Insert the starter chart of accounts, skipping any code already present."""
    existing = {code for (code,) in db.execute(select(Account.code)).all()}
    added = 0
    for code, name, account_type, segment, normal_balance in STARTER_ACCOUNTS:
        if code in existing:
            continue
        db.add(
            Account(
                code=code,
                name_en=name,
                account_type=account_type,
                segment=segment,
                normal_balance=normal_balance,
            )
        )
        added += 1
    db.flush()
    return added
