from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..deps import get_db
from ..db import models
from ..security import verify_password
from ..schemas.metrics import MetricIn
from ..schemas.productivity import WebActivityIn
from ..services.categorizer import categorize_domain
from ..ws import ws_manager

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

def _auth_agent(db: Session, client_id: int, agent_key: str) -> models.Client:
    c = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not c:
        raise HTTPException(404, "Client not found")
    if not verify_password(agent_key, c.agent_key_hash):
        raise HTTPException(401, "Invalid agent key")
    return c

@router.post("/{client_id}/metrics")
async def ingest_metrics(client_id: int, payload: MetricIn, x_agent_key: str = Header(..., alias="X-Agent-Key"), db: Session = Depends(get_db)):
    c = _auth_agent(db, client_id, x_agent_key)
    ts = payload.ts or datetime.now(timezone.utc)
    m = models.Metric(client_id=client_id, ts=ts, cpu=payload.cpu, ram=payload.ram, disk=payload.disk,
                      rx_kbps=payload.rx_kbps, tx_kbps=payload.tx_kbps, connections=payload.connections)
    c.last_seen = datetime.now(timezone.utc)
    c.status = "online"
    db.add(m); db.commit()

    await ws_manager.broadcast("realtime", {"type":"metric", "client_id":client_id, "ts": ts.isoformat(),
                                           "cpu":payload.cpu,"ram":payload.ram,"disk":payload.disk,
                                           "rx_kbps":payload.rx_kbps,"tx_kbps":payload.tx_kbps,"connections":payload.connections})
    return {"ok": True}

@router.post("/{client_id}/web")
async def ingest_web(client_id: int, payload: WebActivityIn, x_agent_key: str = Header(..., alias="X-Agent-Key"), db: Session = Depends(get_db)):
    _auth_agent(db, client_id, x_agent_key)
    ts = payload.ts or datetime.now(timezone.utc)

    # Check for existing record to prevent duplication (idempotency)
    existing = (db.query(models.WebActivity)
                .filter(models.WebActivity.client_id == client_id)
                .filter(models.WebActivity.ts == ts)
                .filter(models.WebActivity.url_hash == payload.url_hash)
                .first())

    if existing:
        return {"ok": True, "detail": "already_exists"}

    # Server-side categorization safeguard
    category = payload.category or categorize_domain(payload.domain)

    w = models.WebActivity(client_id=client_id, user_label=payload.user_label, ts=ts, domain=payload.domain,
                           url_hash=payload.url_hash, category=category)
    db.add(w); db.commit()
    await ws_manager.broadcast("realtime", {"type":"web", "client_id":client_id, "ts": ts.isoformat(),
                                           "domain":payload.domain, "category":category})
    return {"ok": True}