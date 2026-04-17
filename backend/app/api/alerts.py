"""
API endpoints for managing system alerts.
Provides functionality to list alerts and acknowledge/close them.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..deps import get_db, require_role
from ..db import models
from ..schemas.alerts import AlertOut, AlertAck
from ..schemas.common import Msg

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.get("", response_model=list[AlertOut])
def list_alerts(limit: int = 200, db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    """
    Retrieve a list of recent alerts.
    
    Args:
        limit: Maximum number of alerts to return (default 200).
        db: Database session.
        _: Authorization dependency ensuring at least readonly access.
        
    Returns:
        List of Alert objects ordered by timestamp descending.
    """
    return db.query(models.Alert).order_by(models.Alert.ts.desc()).limit(limit).all()

@router.patch("/{alert_id}", response_model=Msg)
def ack(alert_id: int, payload: AlertAck, db: Session = Depends(get_db), user=Depends(require_role("admin","analyst"))):
    """
    Acknowledge or close an alert.
    
    Args:
        alert_id: ID of the alert to update.
        payload: Update data (new status).
        db: Database session.
        user: Authenticated user with admin or analyst role.
        
    Returns:
        Success message.
        
    Raises:
        HTTPException 404: If alert not found.
        HTTPException 400: If invalid status provided.
    """
    # Find the alert in the database
    a = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not a:
        raise HTTPException(404, "Alert not found")
    
    # Validate the status change
    if payload.status not in ("ack","closed"):
        raise HTTPException(400, "Invalid status")
    
    # Update status and record who acknowledged it
    a.status = payload.status
    a.acknowledged_by = user.email
    db.commit()
    return Msg(message="Updated")
