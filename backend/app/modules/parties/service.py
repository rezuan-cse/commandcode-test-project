"""Business logic for customer and supplier records.

The rules here are the ones that keep the list usable as the books grow: a code
is fixed once transactions point at it, a partner named on a posted transaction
is deactivated rather than deleted, and names already on old transactions can be
adopted in one step.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import PartyKind
from app.core.exceptions import DomainError, DuplicateError, NotFoundError
from app.modules.parties import repository
from app.modules.parties.models import Party
from app.modules.parties.schemas import (
    PartyImportResult,
    PartyIn,
    PartyOut,
    PartyUpdate,
)

# Codes are chosen for an adopted partner so the list stays readable: CUS for a
# customer, SUP for a supplier, PAR where the firm is both.
_PREFIX: dict[PartyKind, str] = {
    PartyKind.CUSTOMER: "CUS",
    PartyKind.SUPPLIER: "SUP",
    PartyKind.BOTH: "PAR",
}


def _clean(value: str | None) -> str | None:
    """Trim an optional text field, treating blank as absent.

    An empty string and NULL mean different things to a database, and a form that
    submits "" for every untouched box would fill the record with blanks.
    """
    if value is None:
        return None
    text = value.strip()
    return text or None


def list_parties(
    db: Session,
    *,
    search: str | None = None,
    kind: PartyKind | None = None,
    active_only: bool = False,
) -> list[PartyOut]:
    """List customers and suppliers."""
    return [
        PartyOut.model_validate(party)
        for party in repository.list_parties(
            db, search=search, kind=kind, active_only=active_only
        )
    ]


def get_party(db: Session, code: str) -> Party:
    """Fetch a party or raise :class:`NotFoundError`."""
    party = repository.get_party(db, code)
    if party is None:
        raise NotFoundError(f"Customer or supplier {code} not found")
    return party


def create_party(db: Session, payload: PartyIn) -> PartyOut:
    """Add a customer or supplier.

    A partner whose name already appears on past transactions is the same
    partner, so those transactions are linked to the new record immediately —
    that link is what makes a balance answerable.
    """
    code = payload.code.strip().upper()
    if not code:
        raise DomainError("A customer or supplier needs a code.")
    if repository.get_party(db, code) is not None:
        raise DuplicateError(f"{code} already exists")

    party = Party(
        code=code,
        name=payload.name.strip(),
        kind=payload.kind,
        contact_person=_clean(payload.contact_person),
        phone=_clean(payload.phone),
        email=_clean(payload.email),
        address=_clean(payload.address),
        credit_days=payload.credit_days,
        is_active=payload.is_active,
    )
    repository.add_party(db, party)
    repository.link_transactions(db, party)
    db.commit()
    return PartyOut.model_validate(party)


def update_party(db: Session, code: str, payload: PartyUpdate) -> PartyOut:
    """Correct a record. Only the fields supplied are touched.

    The code cannot change, because posted transactions point at it. Renaming is
    allowed: a firm that changes its name is the same firm, and the code keeps the
    history together.
    """
    party = get_party(db, code)
    supplied = payload.model_dump(exclude_unset=True)

    if supplied.get("name") is not None:
        party.name = supplied["name"].strip()
    if supplied.get("kind") is not None:
        party.kind = supplied["kind"]
    for field in ("contact_person", "phone", "email", "address"):
        if field in supplied:
            setattr(party, field, _clean(supplied[field]))
    if "credit_days" in supplied:
        party.credit_days = supplied["credit_days"]
    if supplied.get("is_active") is not None:
        party.is_active = supplied["is_active"]

    repository.link_transactions(db, party)
    db.commit()
    return PartyOut.model_validate(party)


def delete_party(db: Session, code: str) -> None:
    """Remove a record that nothing points at.

    Refused once a posted transaction names it: deleting would leave that
    transaction's partner unresolved, and its history unreachable. Set the
    record **inactive** instead — it stays readable and simply stops being
    offered on new sales and purchases.
    """
    party = get_party(db, code)
    used = repository.history_count(db, code)
    if used:
        raise DomainError(
            f"{code} is named on {used} posted transaction(s) and cannot be "
            f"deleted. Set it to inactive instead: the history stays, and it "
            f"stops being offered on new sales and purchases."
        )
    repository.delete_party(db, party)
    db.commit()


def import_existing(db: Session) -> PartyImportResult:
    """Adopt the names already on posted sales and purchases as records.

    This is the migration path for a client who has been trading for years: their
    trading partners are already in the system inside the transaction rows, so
    they are adopted rather than retyped. Each adopted record then claims the
    transactions that carry its name, which is what lets a balance exist at all.
    """
    known = {party.name.strip().lower(): party for party in repository.list_parties(db)}
    created: list[str] = []
    already = 0
    linked = 0

    for name, kind in repository.names_on_transactions(db):
        key = name.strip().lower()
        party = known.get(key)
        if party is not None:
            already += 1
            linked += repository.link_transactions(db, party)
            # A firm found on both sides of the books is both, however it was
            # first recorded.
            if party.kind is not kind and PartyKind.BOTH not in (party.kind, kind):
                party.kind = PartyKind.BOTH
            continue

        party = Party(
            code=repository.next_code(db, _PREFIX[kind]),
            name=name.strip(),
            kind=kind,
        )
        repository.add_party(db, party)
        known[key] = party
        created.append(party.code)
        linked += repository.link_transactions(db, party)

    db.commit()
    return PartyImportResult(
        created=len(created),
        already_known=already,
        codes=sorted(created),
        linked=linked,
    )
