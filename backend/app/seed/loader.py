"""Loads the parsed workbook into the database, in dependency order.

The seeder is idempotent: if accounts already exist it does nothing. Historical
inventory rows keep the values the client recorded, so the imported stock
ledger matches their sheet exactly; everything posted from the app afterwards
is computed by the costing engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import (
    AccountType,
    ItemCategory,
    JournalSource,
    MovementType,
    NormalBalance,
    Role,
    Segment,
)
from app.core.money import money, to_decimal
from app.modules.accounts.models import Account
from app.modules.inventory_ledger import service as ledger
from app.modules.inventory_ledger.models import InventoryLedgerRow
from app.modules.items_bom.models import BomComponent, Item
from app.modules.journal_entries import repository as journal_repo
from app.modules.journal_entries import service as journal_service
from app.modules.journal_entries.schemas import JournalLineIn
from app.modules.opening_balances.models import OpeningBalance
from app.modules.users_roles.models import User
from app.seed.excel import WorkbookData, load_workbook_data


@dataclass
class SeedReport:
    """Outcome of a seeding attempt."""

    seeded: bool
    counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Human-readable one-liner for the startup log."""
        if not self.seeded:
            return "already seeded, nothing to do"
        parts = ", ".join(f"{k}={v}" for k, v in self.counts.items())
        return f"seeded {parts}"


DEMO_USERS = [
    ("admin@rpci.demo", "System Administrator", Role.ADMIN),
    ("accountant@rpci.demo", "Chief Accountant", Role.ACCOUNTANT),
    ("store@rpci.demo", "Store & Production", Role.STORE_PRODUCTION),
    ("sales@rpci.demo", "Sales Desk", Role.SALES_STAFF),
    ("owner@rpci.demo", "Owner", Role.OWNER_VIEWER),
]


def is_already_seeded(db: Session) -> bool:
    """True when the chart of accounts is already populated."""
    return db.execute(select(func.count()).select_from(Account)).scalar_one() > 0


def _load_accounts(db: Session, data: WorkbookData) -> None:
    """Insert every chart-of-accounts row."""
    for row in data.accounts:
        db.add(
            Account(
                code=row["code"],
                name_en=row["name_en"],
                account_type=AccountType(row["account_type"]),
                segment=Segment(row["segment"]),
                normal_balance=NormalBalance(row["normal_balance"]),
            )
        )
    db.flush()


def _load_items(db: Session, data: WorkbookData) -> None:
    """Insert every item master row."""
    for row in data.items:
        db.add(
            Item(
                code=row["code"],
                name=row["name"],
                category=ItemCategory(row["category"]),
                segment=Segment(row["segment"]),
                uom=row["uom"],
            )
        )
    db.flush()


def _load_bom(db: Session, data: WorkbookData) -> None:
    """Insert BOM edges."""
    for row in data.bom:
        db.add(
            BomComponent(
                parent_code=row["parent_code"],
                component_code=row["component_code"],
                qty_per_unit=to_decimal(row["qty_per_unit"]),
                stage=row["stage"],
            )
        )
    db.flush()


def _load_opening_balances(db: Session, data: WorkbookData) -> None:
    """Insert the cutover opening trial balance, marked as locked."""
    cutover = data.cutover_date or date.today()
    segment_by_code = {row["code"]: row["segment"] for row in data.accounts}
    for row in data.opening_balances:
        db.add(
            OpeningBalance(
                account_code=row["account_code"],
                segment=Segment(segment_by_code.get(row["account_code"], "Shared")),
                debit=money(row["debit"]),
                credit=money(row["credit"]),
                as_of_date=cutover,
                locked=True,
                locked_by="import",
            )
        )
    db.flush()


def _load_journal_entries(db: Session, data: WorkbookData) -> None:
    """Insert the historical journal entries, preserving voucher numbers."""
    cutover = data.cutover_date or date.today()
    for entry in data.journal_entries:
        if journal_repo.get_by_voucher(db, entry["voucher_no"]) is not None:
            continue
        lines = [
            JournalLineIn(
                account_code=line["account_code"],
                segment=Segment(line["segment"]),
                debit=money(line["debit"]),
                credit=money(line["credit"]),
                narration=line["narration"],
            )
            for line in entry["lines"]
        ]
        built = journal_service.build_entry(
            voucher_no=entry["voucher_no"],
            entry_date=entry["entry_date"] or cutover,
            lines=lines,
            source=JournalSource.MANUAL,
            narration=entry["narration"],
            reference=entry["voucher_no"],
            posted_by=entry["posted_by"],
        )
        journal_repo.add_entry(db, built)
    db.flush()


def _load_inventory(db: Session, data: WorkbookData) -> None:
    """Replay the historical stock movements, keeping recorded out-values.

    Movements are applied in sheet order per item, which is the order the
    client recorded them in. Passing an explicit ``out_value`` preserves their
    figures rather than recomputing at average cost.
    """
    cutover = data.cutover_date or date.today()
    for row in data.inventory:
        is_increase = row["movement_type"] in {
            MovementType.OPENING,
            MovementType.PURCHASE_IN,
            MovementType.PRODUCTION_IN,
        }
        if is_increase:
            ledger.record_movement(
                db,
                item_code=row["item_code"],
                movement_type=MovementType(row["movement_type"]),
                movement_date=row["movement_date"] or cutover,
                qty=to_decimal(row["in_qty"]),
                reference=row["reference"] or "OPENING-IMPORT",
                out_value=to_decimal(row["in_value"]),
            )
        elif to_decimal(row["out_qty"]) > 0:
            ledger.record_movement(
                db,
                item_code=row["item_code"],
                movement_type=MovementType(row["movement_type"]),
                movement_date=row["movement_date"] or cutover,
                qty=to_decimal(row["out_qty"]),
                reference=row["reference"] or "HISTORIC-OUT",
                out_value=to_decimal(row["out_value"]),
            )
    db.flush()


def _load_users(db: Session) -> None:
    """Insert one demo user per role, each with the shared demo password.

    The password is hashed with bcrypt like any other, so the demo exercises the
    same sign-in path as production. It comes from RPCI_DEMO_PASSWORD and is
    listed on the sign-in screen, which is what lets a reviewer switch roles by
    signing out and back in.
    """
    from app.core.security import hash_password

    password_hash = hash_password(settings.demo_password)
    for email, name, role in DEMO_USERS:
        db.add(
            User(
                email=email,
                full_name=name,
                role=role,
                password_hash=password_hash,
            )
        )
    db.flush()


def ensure_demo_users(db: Session) -> list[str]:
    """Make sure each demo account exists and can be signed into.

    Runs on every boot, and is deliberately conservative:

    * a missing account is created;
    * an account with no password gets one, which repairs users seeded before
      passwords existed;
    * an account that already has a password is **left alone**, so a password
      someone has changed is never quietly reset back to the demo default.

    Returns the addresses it touched, for the startup log.
    """
    from app.core.security import hash_password

    repaired: list[str] = []
    default_hash = hash_password(settings.demo_password)

    for email, name, role in DEMO_USERS:
        existing = db.execute(
            select(User).where(func.lower(User.email) == email.lower())
        ).scalar_one_or_none()

        if existing is None:
            db.add(
                User(email=email, full_name=name, role=role, password_hash=default_hash)
            )
            repaired.append(email)
            continue

        if not existing.has_password:
            existing.password_hash = default_hash
            repaired.append(email)

    db.flush()
    return repaired


def seed_if_empty(db: Session) -> SeedReport:
    """Seed the database from the workbook when it is empty.

    Returns a report describing what happened. Safe to call on every startup.
    """
    if is_already_seeded(db):
        return SeedReport(seeded=False, counts={"accounts": 0})

    data = load_workbook_data(settings.seed_from_excel_path)

    _load_accounts(db, data)
    _load_items(db, data)
    _load_bom(db, data)
    _load_opening_balances(db, data)
    _load_journal_entries(db, data)
    _load_inventory(db, data)
    _load_users(db)

    db.commit()

    counts = {
        "accounts": len(data.accounts),
        "items": len(data.items),
        "bom_edges": len(data.bom),
        "opening_balances": len(data.opening_balances),
        "journal_entries": len(data.journal_entries),
        "inventory_rows": db.execute(
            select(func.count()).select_from(InventoryLedgerRow)
        ).scalar_one(),
    }
    return SeedReport(seeded=True, counts=counts, warnings=data.warnings)
