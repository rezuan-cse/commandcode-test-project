"""Imports every module's models so SQLAlchemy registers them before ``create_all``."""

from __future__ import annotations

from app.modules.accounts.models import Account  # noqa: F401
from app.modules.inventory_ledger.models import InventoryLedgerRow  # noqa: F401
from app.modules.items_bom.models import BomComponent, Item  # noqa: F401
from app.modules.journal_entries.models import JournalEntry, JournalLine  # noqa: F401
from app.modules.opening_balances.models import OpeningBalance  # noqa: F401
from app.modules.production.models import ProductionLine, ProductionOrder  # noqa: F401
from app.modules.purchases.models import PurchaseLine, PurchaseOrder  # noqa: F401
from app.modules.sales.models import SalesLine, SalesOrder  # noqa: F401
from app.modules.settings.models import Setting  # noqa: F401
from app.modules.users_roles.models import (  # noqa: F401
    AdminAuditLog,
    RecoveryCode,
    User,
)
