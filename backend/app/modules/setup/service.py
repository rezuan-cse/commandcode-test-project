"""Business logic for first-run setup and the setup checklist."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import JournalSource, PartyKind, Role
from app.core.exceptions import DuplicateError
from app.core.period import fiscal_start_for
from app.core.security import create_token
from app.modules.auth import service as auth_service
from app.modules.auth.schemas import SessionResponse
from app.modules.items_bom.models import BomComponent, Item
from app.modules.journal_entries.models import JournalEntry
from app.modules.parties.models import Party
from app.modules.sales.models import SalesOrder
from app.modules.settings import service as settings_service
from app.modules.settings.models import Setting
from app.modules.setup.schemas import (
    SetupAdminRequest,
    SetupChecklist,
    SetupChecklistItem,
    SetupState,
)
from app.modules.users_roles import service as access_service
from app.modules.users_roles.models import User


def _count(db: Session, model) -> int:
    """How many rows of a table exist."""
    return db.execute(select(func.count()).select_from(model)).scalar_one()


def user_count(db: Session) -> int:
    """How many accounts can sign in."""
    return _count(db, User)


def needs_setup(db: Session) -> bool:
    """True while the system has no account at all."""
    return user_count(db) == 0


def state(db: Session) -> SetupState:
    """Whether setup is still required, and what the company is called."""
    name = settings_service.get_str(db, "company.name", "").strip()
    return SetupState(
        needs_setup=needs_setup(db),
        company_name=name or "your company",
    )


def create_first_admin(db: Session, payload: SetupAdminRequest) -> SessionResponse:
    """Create the first administrator and hand back a session.

    One-shot by construction. The settings row is locked for the duration of the
    transaction, so two requests arriving together cannot both find an empty user
    table and each create an administrator — the second waits, then sees the first
    and is refused. The lock is a no-op on SQLite, where concurrent first-run
    requests are not a real scenario.
    """
    db.execute(
        select(Setting)
        .where(Setting.key == "company.name")
        .with_for_update()
    ).scalar_one_or_none()

    if user_count(db) != 0:
        raise DuplicateError(
            "This system already has an administrator. Sign in, or ask an "
            "administrator to reset your password from Roles & Access."
        )

    email = payload.email.strip().lower()
    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        role=Role.ADMIN,
    )
    db.add(user)
    db.flush()
    auth_service.set_user_password(db, user, payload.password)
    db.commit()

    return SessionResponse(
        access_token=create_token(user.id, user.role.value),
        expires_in_minutes=settings.access_token_minutes,
        user=access_service.to_user_out(db, user),
    )


def suggested_period(db: Session) -> tuple[date, date]:
    """A sensible reporting period for the interface to open on.

    The interface used to hardcode the sample workbook's dates, so a company with no
    workbook posted everything dated 2026-10-31 unless it noticed the top bar. Here:
    the period ends at the latest posting if there is one — which is what a company
    with imported history wants — and otherwise at today.
    """
    latest = db.execute(select(func.max(JournalEntry.entry_date))).scalar_one_or_none()
    as_of = latest or date.today()
    return fiscal_start_for(db, as_of), as_of


def _has_party(db: Session, kind: PartyKind) -> bool:
    """True when a party of this kind, or one that is both, exists."""
    stmt = select(func.count()).select_from(Party).where(
        Party.kind.in_([kind, PartyKind.BOTH])
    )
    return db.execute(stmt).scalar_one() > 0


def checklist(db: Session) -> SetupChecklist:
    """The steps from an empty system to a first sale, and which are done.

    Every answer is computed from data that already exists, so there is nothing to
    keep in step and nothing to reset: a company that imports a workbook simply
    finds most of it already ticked.

    Advisory only — nothing here blocks a posting.
    """
    name = settings_service.get_str(db, "company.name", "").strip()
    address = settings_service.get_str(db, "company.address", "").strip()
    bin_no = settings_service.get_str(db, "company.vat_reg_no", "").strip()

    has_manual_entry = (
        db.execute(
            select(func.count())
            .select_from(JournalEntry)
            .where(JournalEntry.source == JournalSource.MANUAL)
        ).scalar_one()
        > 0
    )

    items = [
        SetupChecklistItem(
            key="company",
            label="Company details recorded",
            detail=(
                "The name, address and VAT registration printed on every invoice. "
                "Set them under Administration → Configuration → Company details."
            ),
            link="/settings",
            done=bool(name and address and bin_no),
        ),
        SetupChecklistItem(
            key="vat",
            label="VAT switched on at the standard rate",
            detail=(
                "VAT is applied to sales from the first invoice. Confirm the rate "
                "with your accountant under Configuration → VAT."
            ),
            link="/settings",
            done=settings_service.get_bool(db, "vat.charge_vat"),
        ),
        SetupChecklistItem(
            key="team",
            label="Your team can sign in",
            detail=(
                "Add the people who will use the system, each with the role that "
                "matches their job."
            ),
            link="/access",
            done=user_count(db) >= 2,
        ),
        SetupChecklistItem(
            key="opening",
            label="Opening capital recorded",
            detail=(
                "A new company's first entry: debit the bank account and credit "
                "share capital for the amount introduced. Post it from Journal "
                "Entries → New journal entry."
            ),
            link="/journal",
            done=has_manual_entry,
        ),
        SetupChecklistItem(
            key="items",
            label="Your products and materials entered",
            detail=(
                "Add what you buy and what you make. Quantity and average cost are "
                "driven by transactions, so they start at zero."
            ),
            link="/inventory",
            done=_count(db, Item) > 0,
        ),
        SetupChecklistItem(
            key="recipes",
            label="Recipes defined",
            detail=(
                "What one unit of each finished product is made from. Open an item "
                "under Inventory & BOM and add its components."
            ),
            link="/inventory",
            done=_count(db, BomComponent) > 0,
        ),
        SetupChecklistItem(
            key="parties",
            label="Customers and suppliers added",
            detail=(
                "One of each is enough to start; a business customer's BIN is "
                "printed on the tax invoice."
            ),
            link="/parties",
            done=_has_party(db, PartyKind.CUSTOMER) and _has_party(db, PartyKind.SUPPLIER),
        ),
        SetupChecklistItem(
            key="first_sale",
            label="First sale posted",
            detail=(
                "Once a sale is posted, the reports, the stock ledger and the "
                "customer's balance all come to life."
            ),
            link="/sales",
            done=_count(db, SalesOrder) > 0,
        ),
    ]

    return SetupChecklist(items=items, complete=all(item.done for item in items))
