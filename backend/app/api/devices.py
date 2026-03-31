from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from ..deps import get_db, require_role
from ..db import models
from ..schemas.devices import DeviceCreate, DeviceOut, DeviceCheckOut
from ..schemas.common import Msg
from .. import audit

router = APIRouter(prefix="/api/devices", tags=["devices"])

@router.get("", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    return db.query(models.Device).order_by(models.Device.id.asc()).all()

@router.post("", response_model=DeviceOut)
async def add_device(payload: DeviceCreate, db: Session = Depends(get_db), user=Depends(require_role("admin","analyst"))):
    d = models.Device(**payload.model_dump())
    db.add(d); db.flush(); db.refresh(d)
    audit.log(db, user.email, "add_device", "device", d.id,
              meta={"name": d.name, "host": d.host})
    db.commit()
    
    # If SNMP is enabled, try an initial poll immediately in the background
    if d.snmp_enabled:
        from .. import jobs
        import asyncio
        asyncio.create_task(jobs._job_snmp_checks())
        
    return d

@router.delete("/{device_id}", response_model=Msg)
def delete_device(device_id: int, db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    d = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not d:
        raise HTTPException(404, "Device not found")
    audit.log(db, user.email, "delete_device", "device", device_id,
              meta={"name": d.name, "host": d.host})
    db.delete(d); db.commit()
    return Msg(message="Deleted")

@router.get("/{device_id}/checks", response_model=list[DeviceCheckOut])
def checks(device_id: int, minutes: int = 120, db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    q = (db.query(models.DeviceCheck)
         .filter(models.DeviceCheck.device_id == device_id)
         .filter(models.DeviceCheck.ts >= since)
         .order_by(models.DeviceCheck.ts.asc()))
    return q.all()
