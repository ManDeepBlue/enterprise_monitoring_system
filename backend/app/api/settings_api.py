"""
API endpoints for managing system configuration settings.
Allows administrators to view and update system-wide keys and values.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..deps import get_db, require_role
from ..db import models
from ..schemas.settings import SettingOut, SettingUpsert
from ..schemas.common import Msg
from .. import audit

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("", response_model=list[SettingOut])
def list_settings(db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    """
    Retrieve all system settings.
    
    Accessible by admin, analyst, and readonly roles.
    """
    return db.query(models.Setting).all()

@router.put("/{key}", response_model=Msg)
def upsert(key: str, payload: SettingUpsert, db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    """
    Create or update a specific setting key.
    
    Restricted to users with the admin role.
    Logs the action in the audit trail.
    """
    # Check if the setting already exists
    s = db.query(models.Setting).filter(models.Setting.key == key).first()
    if not s:
        # Create new setting if it doesn't exist
        s = models.Setting(key=key, value=payload.value)
        db.add(s)
        action = "create_setting"
    else:
        # Update existing setting value
        s.value = payload.value
        action = "update_setting"
    
    # Audit log the change
    audit.log(db, user.email, action, "setting", key, meta={"value": payload.value})
    
    db.commit()
    return Msg(message="Saved")
