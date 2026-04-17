"""
API endpoints for analyzing client web productivity.
Provides detailed activity logs and category-based summaries.
"""

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
    """
    Get recent web activity for a specific client.
    
    Args:
        client_id: The ID of the client.
        minutes: Lookback window (default 120 minutes).
        
    Returns:
        A list of recent WebActivity records, limited to the 500 most recent.
    """
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    q = (db.query(models.WebActivity)
         .filter(models.WebActivity.client_id == client_id)
         .filter(models.WebActivity.ts >= since)
         .order_by(models.WebActivity.ts.desc())
         .limit(500))
    return q.all()

@router.get("/{client_id}/summary")
def summary(client_id: int, minutes: int = 480, db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    """
    Get a summary of web activity grouped by category.
    
    Useful for visualizing time spent on different types of sites (e.g. Work, Social, News).
    
    Args:
        client_id: The ID of the client.
        minutes: Lookback window (default 480 minutes / 8 hours).
    """
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    
    # Aggregate activity counts by category using SQL GROUP BY
    rows = (db.query(models.WebActivity.category, func.count(models.WebActivity.id).label("count"))
            .filter(models.WebActivity.client_id == client_id)
            .filter(models.WebActivity.ts >= since)
            .group_by(models.WebActivity.category)
            .all())
    
    return {
        "since": since.isoformat(), 
        "by_category": [{"category": c, "count": int(cnt)} for c,cnt in rows]
    }
