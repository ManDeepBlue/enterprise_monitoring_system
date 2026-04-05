# app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager
import os
import logging

# local imports
from .settings import settings
from .db.session import engine, SessionLocal
from .db import models
from .api import auth, clients, ingest, metrics, alerts, devices, scans, productivity, settings_api, analytics, snmp, users
from .deps import get_db, require_role
from .ws import ws_manager
from . import jobs

# --- LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    models.Base.metadata.create_all(bind=engine)
    


    sched = AsyncIOScheduler()
    sched.add_job(jobs._job_alerts, "interval", seconds=15, max_instances=1)
    sched.add_job(jobs._job_mark_offline, "interval", seconds=5, max_instances=1)
    sched.add_job(jobs._job_device_checks, "interval", seconds=settings.default_device_check_interval_sec, max_instances=1)
    sched.add_job(jobs._job_snmp_checks, "interval", seconds=60, max_instances=1)
    sched.start()
    yield
    sched.shutdown()

# --- DATABASE SETUP ---
app = FastAPI(title=settings.app_name, lifespan=lifespan)

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
app.include_router(users.router)
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
    candidate = Path(__file__).resolve().parents[2] / "frontend" / "static"
    fallback = Path("/frontend/static")
    if candidate.exists():
        _frontend_dir = candidate.resolve()
    elif fallback.exists():
        _frontend_dir = fallback.resolve()
    else:
        _frontend_dir = (Path(__file__).resolve().parents[0] / "frontend" / "static").resolve()

_frontend_dir = Path(_frontend_dir)
if not _frontend_dir.exists():
    logging.warning(f"Frontend static directory not found: {_frontend_dir} (frontend routes will return 404).")

app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="static")
_INDEX_FILE = _frontend_dir / "index.html"


@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/db-stats")
def db_stats(db: Session = Depends(get_db), user: models.User = Depends(require_role("admin"))):
    from .db import models as m
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
        logs = db.query(m.AuditLog).order_by(m.AuditLog.ts.desc()).limit(50).all()
        log_list = [{"ts": l.ts.isoformat() if l.ts.tzinfo else l.ts.replace(tzinfo=timezone.utc).isoformat(), "user": l.actor_email, "action": l.action, "detail": f"{l.entity} #{l.entity_id}"} for l in logs]
        return {
            "tables": [{"name": n, "rows": c} for n, c in tables],
            "recent_logs": log_list,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logging.exception("Error fetching db stats")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/realtime")
async def ws_realtime(ws: WebSocket):
    await ws_manager.connect("realtime", ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect("realtime", ws)


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend_file(full_path: str, request: Request):
    if request.url.path.startswith("/api/") or request.url.path.startswith("/ws/"):
        raise HTTPException(status_code=404)
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
    if _INDEX_FILE.exists():
        return FileResponse(_INDEX_FILE)
    raise HTTPException(status_code=404, detail=f"File not found: {full_path}")
