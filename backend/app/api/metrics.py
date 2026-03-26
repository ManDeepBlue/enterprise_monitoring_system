from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from ..deps import get_db, require_role
from ..db import models
from ..schemas.metrics import MetricOut

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

@router.get("/{client_id}/latest", response_model=MetricOut | None)
def latest(client_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    m = (db.query(models.Metric).filter(models.Metric.client_id == client_id).order_by(models.Metric.ts.desc()).first())
    return m

@router.get("/{client_id}/range", response_model=list[MetricOut])
def range_metrics(client_id: int, minutes: int = 60, db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    q = (db.query(models.Metric)
         .filter(models.Metric.client_id == client_id)
         .filter(models.Metric.ts >= since)
         .order_by(models.Metric.ts.asc()))
    return q.all()