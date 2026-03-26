from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from ..deps import get_db, require_role
from ..db import models

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/clients/health")
def clients_health(db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    clients = db.query(models.Client).all()
    out = []
    for c in clients:
        latest = (db.query(models.Metric).filter(models.Metric.client_id==c.id).order_by(models.Metric.ts.desc()).first())
        out.append({
            "id": c.id,
            "name": c.name,
            "status": c.status,
            "last_seen": c.last_seen.isoformat() if c.last_seen else None,
            "cpu": latest.cpu if latest else None,
            "ram": latest.ram if latest else None,
            "rx_kbps": latest.rx_kbps if latest else None,
            "tx_kbps": latest.tx_kbps if latest else None,
        })
    return out

@router.get("/forecast/simple")
def simple_forecast(client_id: int, metric: str = "cpu", minutes: int = 240, horizon_points: int = 12,
                    db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    # Simple linear regression forecast for demo/academic use.
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    rows = (db.query(models.Metric.ts, getattr(models.Metric, metric))
            .filter(models.Metric.client_id == client_id)
            .filter(models.Metric.ts >= since)
            .order_by(models.Metric.ts.asc())
            .all())
    if len(rows) < 5:
        return {"metric": metric, "forecast": [], "note": "Not enough data"}
    import numpy as np
    xs = np.arange(len(rows), dtype=float)
    ys = np.array([float(v) for _, v in rows], dtype=float)
    a, b = np.polyfit(xs, ys, 1)
    start = len(rows)
    future_x = np.arange(start, start + horizon_points, dtype=float)
    future_y = (a * future_x + b).tolist()
    return {"metric": metric, "forecast": future_y, "model": {"slope": float(a), "intercept": float(b)}}