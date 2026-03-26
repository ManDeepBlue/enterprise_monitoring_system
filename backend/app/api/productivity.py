
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from ..deps import get_db, require_role
from ..db import models
from ..schemas.productivity import WebActivityOut

router = APIRouter(prefix="/api/productivity", tags=["productivity"])

@router.get("/{client_id}/recent", response_model=list[WebActivityOut])
def recent(client_id: int, minutes: int = 120, db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    q = (db.query(models.WebActivity)
         .filter(models.WebActivity.client_id == client_id)
         .filter(models.WebActivity.ts >= since)
         .order_by(models.WebActivity.ts.desc())
         .limit(500))
    return q.all()

@router.get("/{client_id}/summary")
def summary(client_id: int, minutes: int = 480, db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    rows = (db.query(models.WebActivity.category, func.sum(models.WebActivity.duration_seconds).label("seconds"))
            .filter(models.WebActivity.client_id == client_id)
            .filter(models.WebActivity.ts >= since)
            .group_by(models.WebActivity.category)
            .all())
    return {"since": since.isoformat(), "by_category": [{"category": c, "seconds": int(s)} for c,s in rows]}
