# app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import logging

# local imports
from .settings import settings
from .db.session import make_engine, make_session
from .db import models
from .api import auth, clients, ingest, metrics, alerts, devices, scans, productivity, settings_api, analytics, snmp
from .ws import ws_manager
from .services.alert_engine import eval_metrics, dedupe_and_persist, DEFAULT_THRESHOLDS
from .services.icmp import ping
from .services.snmp import fetch_snmp_interfaces

# --- DATABASE SETUP ---
engine = make_engine(settings.database_url)
SessionLocal = make_session(engine)

app = FastAPI(title=settings.app_name)

# --- SECURITY (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allow_origins.split(",")] if settings.allow_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTES ---
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(ingest.router)
app.include_router(metrics.router)
app.include_router(alerts.router)
app.include_router(devices.router)
app.include_router(scans.router)
app.include_router(productivity.router)
app.include_router(settings_api.router)
app.include_router(analytics.router)
app.include_router(snmp.router)


# --- SERVING THE DASHBOARD ---
_frontend_dir = None
if os.getenv("FRONTEND_DIR"):
    _frontend_dir = Path(os.getenv("FRONTEND_DIR")).resolve()
else:
    # prefer repo-relative frontend/static
    candidate = Path(__file__).resolve().parents[2] / "frontend" / "static"
    fallback = Path("/frontend/static")
    if candidate.exists():
        _frontend_dir = candidate.resolve()
    elif fallback.exists():
        _frontend_dir = fallback.resolve()
    else:
        # last fallback (app-relative)
        _frontend_dir = (Path(__file__).resolve().parents[0] / "frontend" / "static").resolve()

_frontend_dir = Path(_frontend_dir)
if not _frontend_dir.exists():
    logging.warning(f"Frontend static directory not found: {_frontend_dir} (frontend routes will return 404).")

# mount raw static at /static
app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="static")

_INDEX_FILE = _frontend_dir / "index.html"


@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/db-stats")
def db_stats(request: Request):
    from .db import models as m
    # simple auth check
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    db: Session = SessionLocal()
    try:
        tables = [
            ("metrics",      db.query(m.Metric).count()),
            ("web_activity", db.query(m.WebActivity).count()),
            ("alerts",       db.query(m.Alert).count()),
            ("port_findings",db.query(m.PortFinding).count()),
            ("device_checks",db.query(m.DeviceCheck).count()),
            ("audit_log",    db.query(m.AuditLog).count()),
            ("clients",      db.query(m.Client).count()),
            ("users",        db.query(m.User).count()),
        ]
        # recent audit log entries
        logs = db.query(m.AuditLog).order_by(m.AuditLog.ts.desc()).limit(50).all()
        log_list = [{"ts": l.ts.isoformat() if l.ts.tzinfo else l.ts.replace(tzinfo=timezone.utc).isoformat(), "user": l.actor_email, "action": l.action, "detail": f"{l.entity} #{l.entity_id}"} for l in logs]
        return {
            "tables": [{"name": n, "rows": c} for n, c in tables],
            "recent_logs": log_list,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    finally:
        db.close()


@app.websocket("/ws/realtime")
async def ws_realtime(ws: WebSocket):
    await ws_manager.connect("realtime", ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect("realtime", ws)


def _get_setting(db: Session, key: str, default: dict):
    s = db.query(models.Setting).filter(models.Setting.key == key).first()
    return s.value if s else default


# --- BACKGROUND JOBS ---

async def _job_alerts():
    db = SessionLocal()
    try:
        thresholds = _get_setting(db, "alert_thresholds", DEFAULT_THRESHOLDS)
        new_alerts = eval_metrics(db, thresholds)
        created = await dedupe_and_persist(db, new_alerts, window_sec=60)
        if created:
            await ws_manager.broadcast("realtime", {"type": "alerts_updated"})
    except Exception:
        logging.exception("Error in _job_alerts")
    finally:
        db.close()

async def _job_mark_offline():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        interval = _get_setting(db, "monitoring", {"offline_after_sec": 30}).get("offline_after_sec", 30)
        for c in db.query(models.Client).all():
            if not c.last_seen: continue
            last_seen = c.last_seen.replace(tzinfo=timezone.utc) if c.last_seen.tzinfo is None else c.last_seen
            if (now - last_seen) > timedelta(seconds=interval):
                if c.status != "offline":
                    c.status = "offline"
        db.commit()
    except Exception:
        logging.exception("Error in _job_mark_offline")
    finally:
        db.close()

async def _job_device_checks():
    db = SessionLocal()
    try:
        timeout = float(_get_setting(db, "device_checks", {"timeout_sec": 1.0}).get("timeout_sec", 1.0))
        devices_q = db.query(models.Device).filter(models.Device.is_enabled == True).all()
        for d in devices_q:
            ok, ms = await ping(d.host, timeout=timeout)
            db.add(models.DeviceCheck(device_id=d.id, reachable=ok, latency_ms=ms))
        db.commit()
    except Exception:
        logging.exception("Error in _job_device_checks")
    finally:
        db.close()

async def _job_snmp_checks():
    db = SessionLocal()
    try:
        devices_q = db.query(models.Device).filter(models.Device.is_enabled == True, models.Device.snmp_enabled == True).all()
        for d in devices_q:
            try:
                results = await fetch_snmp_interfaces(d.host, d.snmp_community, d.snmp_port)
                for iface in results:
                    db.add(models.SNMPInterfaceStatus(
                        device_id=d.id,
                        interface_index=iface["index"],
                        description=iface["description"],
                        alias=iface.get("alias"),
                        admin_status=iface["admin_status"],
                        oper_status=iface["oper_status"],
                        reason=iface["reason"]
                    ))
                db.commit()
                # Broadcast that SNMP data for this device has been updated
                await ws_manager.broadcast("realtime", {"type": "snmp_updated", "device_id": d.id})
            except Exception:
                logging.exception(f"Error polling SNMP for device {d.host}")
    except Exception:
        logging.exception("Error in _job_snmp_checks")
    finally:
        db.close()


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend_file(full_path: str, request: Request):
    """
    Serve frontend files safely:
      - Protect /api/ and /ws/ from being handled here
      - Serve exact files from the frontend dir
      - Fallback to index.html for SPA routes
    """
    if request.url.path.startswith("/api/") or request.url.path.startswith("/ws/"):
        raise HTTPException(status_code=404)

    # root -> index
    if full_path in ("", "/"):
        if _INDEX_FILE.exists():
            return FileResponse(_INDEX_FILE)
        raise HTTPException(status_code=404)

    target = _frontend_dir / full_path.lstrip("/")
    if target.is_dir():
        index_candidate = target / "index.html"
        if index_candidate.exists():
            return FileResponse(index_candidate)

    if target.exists() and target.is_file():
        return FileResponse(target)

    # SPA fallback
    if _INDEX_FILE.exists():
        return FileResponse(_INDEX_FILE)

    raise HTTPException(status_code=404, detail=f"File not found: {full_path}")


@app.on_event("startup")
async def startup():
    models.Base.metadata.create_all(bind=engine)
    sched = AsyncIOScheduler()
    sched.add_job(_job_alerts, "interval", seconds=15, max_instances=1)
    sched.add_job(_job_mark_offline, "interval", seconds=5, max_instances=1)
    sched.add_job(_job_device_checks, "interval", seconds=settings.default_device_check_interval_sec, max_instances=1)
    sched.add_job(_job_snmp_checks, "interval", seconds=60, max_instances=1)
    sched.start()
