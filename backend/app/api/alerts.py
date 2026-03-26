
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..deps import get_db, require_role
from ..db import models
from ..schemas.alerts import AlertOut, AlertAck
from ..schemas.common import Msg

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.get("", response_model=list[AlertOut])
def list_alerts(limit: int = 200, db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    return db.query(models.Alert).order_by(models.Alert.ts.desc()).limit(limit).all()

@router.patch("/{alert_id}", response_model=Msg)
def ack(alert_id: int, payload: AlertAck, db: Session = Depends(get_db), user=Depends(require_role("admin","analyst"))):
    a = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not a:
        raise HTTPException(404, "Alert not found")
    if payload.status not in ("ack","closed"):
        raise HTTPException(400, "Invalid status")
    a.status = payload.status
    a.acknowledged_by = user.email
    db.commit()
    return Msg(message="Updated")
