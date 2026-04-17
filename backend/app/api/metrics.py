"""
API endpoints for retrieving historical and real-time performance metrics.
Provides access to metrics collected from monitoring agents.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from ..deps import get_db, require_role
from ..db import models
from ..schemas.metrics import MetricOut

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

@router.get("/{client_id}/latest", response_model=MetricOut | None)
def latest(client_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    """
    Get the most recent metric entry for a specific client.
    
    Returns None if the client doesn't exist or is currently offline.
    """
    c = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not c or c.status == "offline":
        return None
        
    m = (db.query(models.Metric)
         .filter(models.Metric.client_id == client_id)
         .order_by(models.Metric.ts.desc())
         .first())
    return m

@router.get("/{client_id}/range", response_model=list[MetricOut])
def range_metrics(client_id: int, minutes: int = 60, db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    """
    Get a range of historical metrics for a specific client.
    
    Args:
        client_id: The ID of the client.
        minutes: Lookback window in minutes (default 60).
        
    Returns:
        List of Metric objects ordered by timestamp ascending.
    """
    c = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not c or c.status == "offline":
        return []
        
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    q = (db.query(models.Metric)
         .filter(models.Metric.client_id == client_id)
         .filter(models.Metric.ts >= since)
         .order_by(models.Metric.ts.asc()))
    return q.all()
