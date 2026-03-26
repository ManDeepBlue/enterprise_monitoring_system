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
    return db.query(models.Setting).all()

@router.put("/{key}", response_model=Msg)
def upsert(key: str, payload: SettingUpsert, db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    s = db.query(models.Setting).filter(models.Setting.key == key).first()
    if not s:
        s = models.Setting(key=key, value=payload.value)
        db.add(s)
        action = "create_setting"
    else:
        s.value = payload.value
        action = "update_setting"
    audit.log(db, user.email, action, "setting", key, meta={"value": payload.value})
    db.commit()
    return Msg(message="Saved")