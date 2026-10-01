"""Thin HTTP routes for customer and supplier records."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.enums import PartyKind
from app.modules.parties import service
from app.modules.parties.schemas import (
    PartyImportResult,
    PartyIn,
    PartyOut,
    PartyUpdate,
)
from app.modules.users_roles.service import Principal, require

router = APIRouter(prefix="/parties", tags=["parties"])

CAN_READ = Depends(require("parties", write=False))


@router.get("", response_model=list[PartyOut], dependencies=[CAN_READ])
def list_parties(
    search: str | None = Query(default=None),
    kind: PartyKind | None = Query(default=None),
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[PartyOut]:
    """List customers and suppliers."""
    return service.list_parties(db, search=search, kind=kind, active_only=active_only)


@router.post("/import-existing", response_model=PartyImportResult)
def import_existing(
    principal: Principal = Depends(require("parties", write=True)),
    db: Session = Depends(get_db),
) -> PartyImportResult:
    """Adopt the customer and supplier names already on posted transactions.

    Declared before ``/{code}`` so the path is not read as a code.
    """
    return service.import_existing(db)


@router.get("/{code}", response_model=PartyOut, dependencies=[CAN_READ])
def get_party(code: str, db: Session = Depends(get_db)) -> PartyOut:
    """Fetch one customer or supplier."""
    return PartyOut.model_validate(service.get_party(db, code))


@router.post("", response_model=PartyOut, status_code=201)
def create_party(
    payload: PartyIn,
    principal: Principal = Depends(require("parties", write=True)),
    db: Session = Depends(get_db),
) -> PartyOut:
    """Add a customer or supplier."""
    return service.create_party(db, payload)


@router.patch("/{code}", response_model=PartyOut)
def update_party(
    code: str,
    payload: PartyUpdate,
    principal: Principal = Depends(require("parties", write=True)),
    db: Session = Depends(get_db),
) -> PartyOut:
    """Correct a record's name, kind, contact details or terms."""
    return service.update_party(db, code, payload)


@router.delete("/{code}")
def delete_party(
    code: str,
    principal: Principal = Depends(require("parties", write=True)),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Remove a record no transaction refers to; otherwise set it inactive."""
    service.delete_party(db, code)
    return {"message": f"{code} deleted"}
