"""Thin HTTP routes for journal entries."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.journal_entries import service
from app.modules.journal_entries.schemas import JournalEntryCreate, JournalEntryOut
from app.modules.users_roles.service import require

router = APIRouter(prefix="/journal-entries", tags=["journal-entries"])

CAN_READ = Depends(require("journal_entries", write=False))
CAN_WRITE = Depends(require("journal_entries", write=True))


@router.get("", response_model=list[JournalEntryOut], dependencies=[CAN_READ])
def list_entries(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
    db: Session = Depends(get_db),
) -> list[JournalEntryOut]:
    """List journal entries."""
    return service.list_entries(db, date_from=date_from, date_to=date_to, limit=limit)


@router.get("/{entry_id}", response_model=JournalEntryOut, dependencies=[CAN_READ])
def get_entry(entry_id: int, db: Session = Depends(get_db)) -> JournalEntryOut:
    """Fetch one journal entry."""
    return service.get_entry(db, entry_id)


@router.post("", response_model=JournalEntryOut, status_code=201, dependencies=[CAN_WRITE])
def post_entry(payload: JournalEntryCreate, db: Session = Depends(get_db)) -> JournalEntryOut:
    """Post a manual journal entry. Rejected if debits != credits."""
    return service.post_manual_entry(db, payload)
