"""
API endpoints for managing monitored network devices.
Provides CRUD operations for devices and access to device check history (ICMP/SNMP).
"""

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
    """
    List all monitored devices.
    
    Accessible by admin, analyst, and readonly roles.
    """
    return db.query(models.Device).order_by(models.Device.id.asc()).all()

@router.post("", response_model=DeviceOut)
async def add_device(payload: DeviceCreate, db: Session = Depends(get_db), user=Depends(require_role("admin","analyst"))):
    """
    Add a new network device to be monitored.
    
    If SNMP is enabled for the device, it triggers an immediate background poll.
    Accessible by admin and analyst roles.
    """
    d = models.Device(**payload.model_dump())
    db.add(d)
    db.flush()
    db.refresh(d)
    
    # Log the addition of a new device
    audit.log(db, user.email, "add_device", "device", d.id,
              meta={"name": d.name, "host": d.host})
    db.commit()
    
    # Trigger an immediate poll if SNMP is enabled to get initial data
    if d.snmp_enabled:
        from .. import jobs
        import asyncio
        # Run the poll in the background so the API request doesn't wait
        asyncio.create_task(jobs._job_snmp_checks())
        
    return d

@router.delete("/{device_id}", response_model=Msg)
def delete_device(device_id: int, db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    """
    Delete a device from monitoring.
    
    Only administrators can delete devices.
    """
    d = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not d:
        raise HTTPException(404, "Device not found")
    
    # Log the deletion
    audit.log(db, user.email, "delete_device", "device", device_id,
              meta={"name": d.name, "host": d.host})
    
    db.delete(d)
    db.commit()
    return Msg(message="Deleted")

@router.get("/all-checks", response_model=list[DeviceCheckOut])
def list_all_checks(limit: int = 100, db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    """
    Get a global list of the most recent device checks across all devices.
    
    Useful for a system-wide activity feed.
    """
    q = (db.query(models.DeviceCheck)
         .order_by(models.DeviceCheck.ts.desc())
         .limit(limit))
    return q.all()

@router.get("/{device_id}/checks", response_model=list[DeviceCheckOut])
def checks(device_id: int, minutes: int = 120, db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    """
    Get historical check results for a specific device.
    
    Args:
        device_id: The ID of the device.
        minutes: The lookback window in minutes (default 120).
    """
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    q = (db.query(models.DeviceCheck)
         .filter(models.DeviceCheck.device_id == device_id)
         .filter(models.DeviceCheck.ts >= since)
         .order_by(models.DeviceCheck.ts.asc()))
    return q.all()
