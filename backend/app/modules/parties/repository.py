"""All database queries for customer and supplier records live here."""

from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.enums import PartyKind
from app.modules.parties.models import Party


def list_parties(
    db: Session,
    *,
    search: str | None = None,
    kind: PartyKind | None = None,
    active_only: bool = False,
) -> list[Party]:
    """List parties, optionally filtered by text, kind, or active state."""
    stmt = select(Party).order_by(Party.name)
    if search:
        needle = f"%{search.lower()}%"
        stmt = stmt.where(
            func.lower(Party.name).like(needle) | func.lower(Party.code).like(needle)
        )
    if kind is not None:
        # A partner marked "both" answers either question, so a customer list has
        # to include the firms that also supply.
        stmt = stmt.where(Party.kind.in_([kind, PartyKind.BOTH]))
    if active_only:
        stmt = stmt.where(Party.is_active.is_(True))
    return list(db.execute(stmt).scalars().all())


def get_party(db: Session, code: str) -> Party | None:
    """Fetch a single party by code."""
    return db.get(Party, code)


def add_party(db: Session, party: Party) -> Party:
    """Persist a party."""
    db.add(party)
    db.flush()
    return party


def delete_party(db: Session, party: Party) -> None:
    """Remove a party row."""
    db.delete(party)
    db.flush()


def history_count(db: Session, code: str) -> int:
    """How many posted transactions point at this party."""
    from app.modules.purchases.models import PurchaseOrder
    from app.modules.sales.models import SalesOrder

    total = 0
    for model in (SalesOrder, PurchaseOrder):
        total += db.execute(
            select(func.count()).select_from(model).where(model.party_code == code)
        ).scalar_one()
    return total


def names_on_transactions(db: Session) -> list[tuple[str, PartyKind]]:
    """Every customer and supplier name already used on a posted transaction.

    Names typed before this list existed are the client's real trading partners,
    so they are the starting point for adopting history rather than asking
    somebody to retype a list from memory.
    """
    from app.modules.purchases.models import PurchaseOrder
    from app.modules.sales.models import SalesOrder

    found: dict[str, dict[str, object]] = {}

    def note(name: str | None, *, customer: bool) -> None:
        text = (name or "").strip()
        if not text:
            return
        entry = found.setdefault(
            text.lower(), {"name": text, "customer": False, "supplier": False}
        )
        if customer:
            entry["customer"] = True
        else:
            entry["supplier"] = True

    for (name,) in db.execute(select(SalesOrder.customer).distinct()):
        note(name, customer=True)
    for (name,) in db.execute(select(PurchaseOrder.supplier).distinct()):
        note(name, customer=False)

    out: list[tuple[str, PartyKind]] = []
    for entry in found.values():
        if entry["customer"] and entry["supplier"]:
            kind = PartyKind.BOTH
        elif entry["customer"]:
            kind = PartyKind.CUSTOMER
        else:
            kind = PartyKind.SUPPLIER
        out.append((str(entry["name"]), kind))
    return out


def link_transactions(db: Session, party: Party) -> int:
    """Point posted transactions carrying this party's name at its record.

    Matching is on the trimmed, case-folded name, so a name typed with different
    capitalisation is recognised as the same partner. Only rows with no link are
    touched, so a deliberate link is never overwritten.
    """
    from app.modules.purchases.models import PurchaseOrder
    from app.modules.sales.models import SalesOrder

    wanted = party.name.strip().lower()
    updated = 0

    result = db.execute(
        update(SalesOrder)
        .where(func.lower(func.trim(SalesOrder.customer)) == wanted)
        .where(SalesOrder.party_code.is_(None))
        .values(party_code=party.code)
    )
    updated += result.rowcount or 0

    result = db.execute(
        update(PurchaseOrder)
        .where(func.lower(func.trim(PurchaseOrder.supplier)) == wanted)
        .where(PurchaseOrder.party_code.is_(None))
        .values(party_code=party.code)
    )
    updated += result.rowcount or 0
    return updated


def next_code(db: Session, prefix: str) -> str:
    """The next free code for a prefix, e.g. CUS-004."""
    taken = {
        code
        for (code,) in db.execute(
            select(Party.code).where(Party.code.like(f"{prefix}-%"))
        )
    }
    number = 1
    while f"{prefix}-{number:03d}" in taken:
        number += 1
    return f"{prefix}-{number:03d}"
