"""
Main Application Entry Point
----------------------------
This module initializes the FastAPI application, configures middleware,
registers API routers, sets up background tasks (scheduler), and 
handles the serving of the frontend static files.
"""

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
    """
    Handles application startup and shutdown events.
    - Creates database tables if they don't exist.
    - Initializes and starts the background task scheduler.
    - Shuts down the scheduler on application exit.
    """
    # Ensure tables exist (Alembic is preferred for production)
    models.Base.metadata.create_all(bind=engine)

    # Initialize AsyncIOScheduler for background jobs
    sched = AsyncIOScheduler()
    
    # 1. Alert evaluation job (every 15s)
    sched.add_job(jobs._job_alerts, "interval", seconds=15, max_instances=1)
    
    # 2. Mark clients offline if they haven't sent metrics recently (every 5s)
    sched.add_job(jobs._job_mark_offline, "interval", seconds=5, max_instances=1)
    
    # 3. ICMP/Port checks for network devices
    sched.add_job(jobs._job_device_checks, "interval", 
                  seconds=settings.default_device_check_interval_sec, 
                  max_instances=1)
    
    # 4. SNMP polling job (every 60s)
    sched.add_job(jobs._job_snmp_checks, "interval", seconds=60, max_instances=1)
    
    sched.start()
    
    yield # Application runs here
    
    # Shutdown scheduler cleanly
    sched.shutdown()

# --- APP INITIALIZATION ---
app = FastAPI(title=settings.app_name, lifespan=lifespan)

# --- SECURITY (CORS) ---
# Configure Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allow_origins.split(",")] if settings.allow_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTE REGISTRATION ---
# Include all sub-routers for different functional areas
app.include_router(auth.router)           # Authentication & Token management
app.include_router(users.router)          # User management
app.include_router(clients.router)        # Monitored client management
app.include_router(ingest.router)         # Metric & Activity ingestion
app.include_router(metrics.router)        # Metric retrieval & analysis
app.include_router(alerts.router)         # Alert configuration & history
app.include_router(devices.router)        # Network device management
app.include_router(scans.router)          # Vulnerability scanning management
app.include_router(productivity.router)   # Web activity & productivity reports
app.include_router(settings_api.router)   # System-wide settings
app.include_router(analytics.router)      # High-level data analytics
app.include_router(snmp.router)           # SNMP monitoring configuration


# --- STATIC FILE SERVING CONFIGURATION ---
# Determine the directory where frontend static files are located
_frontend_dir = None
if os.getenv("FRONTEND_DIR"):
    _frontend_dir = Path(os.getenv("FRONTEND_DIR")).resolve()
else:
    # Try common relative paths for development and Docker environments
    candidate = Path(__file__).resolve().parents[2] / "frontend" / "static"
    fallback = Path("/frontend/static")
    if candidate.exists():
        _frontend_dir = candidate.resolve()
    elif fallback.exists():
        _frontend_dir = fallback.resolve()
    else:
        # Last resort fallback
        _frontend_dir = (Path(__file__).resolve().parents[0] / "frontend" / "static").resolve()

_frontend_dir = Path(_frontend_dir)
if not _frontend_dir.exists():
    logging.warning(f"Frontend static directory not found: {_frontend_dir} (frontend routes will return 404).")

# Mount the static directory for CSS, JS, and Images
app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="static")
_INDEX_FILE = _frontend_dir / "index.html"


@app.get("/api/health")
def health():
    """Simple health check endpoint."""
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/db-stats")
def db_stats(db: Session = Depends(get_db), user: models.User = Depends(require_role("admin"))):
    """
    Returns administrative statistics about database usage and recent audit logs.
    Restricted to 'admin' role.
    """
    from .db import models as m
    try:
        # Count rows in major tables
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
        # Fetch 50 most recent audit logs
        logs = db.query(m.AuditLog).order_by(m.AuditLog.ts.desc()).limit(50).all()
        log_list = [
            {
                "ts": l.ts.isoformat() if l.ts.tzinfo else l.ts.replace(tzinfo=timezone.utc).isoformat(), 
                "user": l.actor_email, 
                "action": l.action, 
                "detail": f"{l.entity} #{l.entity_id}"
            } for l in logs
        ]
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
    """
    WebSocket endpoint for real-time dashboard updates.
    Broadcasts metrics as they arrive.
    """
    await ws_manager.connect("realtime", ws)
    try:
        while True:
            # Keep connection alive; wait for messages or disconnect
            await ws.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect("realtime", ws)


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend_file(full_path: str, request: Request):
    """
    Catch-all route to serve the SPA (Single Page Application) frontend.
    - If a specific file exists, it is served.
    - Otherwise, falls back to index.html (client-side routing support).
    - Ignores paths starting with /api/ or /ws/.
    """
    if request.url.path.startswith("/api/") or request.url.path.startswith("/ws/"):
        raise HTTPException(status_code=404)
    
    # Handle root path
    if full_path in ("", "/"):
        if _INDEX_FILE.exists():
            return FileResponse(_INDEX_FILE)
        raise HTTPException(status_code=404)
    
    target = _frontend_dir / full_path.lstrip("/")
    
    # Serve index.html if a directory is requested and it contains index.html
    if target.is_dir():
        index_candidate = target / "index.html"
        if index_candidate.exists():
            return FileResponse(index_candidate)
            
    # Serve the exact file if it exists
    if target.exists() and target.is_file():
        return FileResponse(target)
        
    # SPA fallback: Serve index.html for all other routes to allow client-side routing
    if _INDEX_FILE.exists():
        return FileResponse(_INDEX_FILE)
        
    raise HTTPException(status_code=404, detail=f"File not found: {full_path}")
