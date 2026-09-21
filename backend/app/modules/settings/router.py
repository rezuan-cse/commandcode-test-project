"""Thin HTTP routes for the settings store."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.settings import service
from app.modules.settings.schemas import SettingOut, SettingUpdate
from app.modules.users_roles.service import require_admin

router = APIRouter(prefix="/settings", tags=["settings"])

ADMIN_ONLY = Depends(require_admin())


@router.get("", response_model=list[SettingOut])
def list_settings(db: Session = Depends(get_db)) -> list[SettingOut]:
    """List all configurable settings. Readable by any signed-in role."""
    return service.list_settings(db)


@router.patch("/{key}", response_model=SettingOut, dependencies=[ADMIN_ONLY])
def update_setting(
    key: str, payload: SettingUpdate, db: Session = Depends(get_db)
) -> SettingOut:
    """Update a setting value. Admin only."""
    return service.update_setting(db, key, payload)
