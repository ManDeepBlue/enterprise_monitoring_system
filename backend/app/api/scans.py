"""
API endpoints for managing security scans.
Handles port scanning operations, run tracking, and finding retrieval.
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..deps import get_db, require_role
from ..db import models
from ..schemas.scans import ScanRequest, ScanRunOut, FindingOut
from ..services.scanner import scan_ports, TOP_PORTS
from ..services.risk import score_port, level, recommendation_for

router = APIRouter(prefix="/api/scans", tags=["security"])

async def _run_scan(db_url: str, run_id: int):
    """
    Background worker function that performs the port scan and records results.
    
    Args:
        db_url: The database connection URL.
        run_id: The ID of the PortScanRun record.
    """
    # Lazy import to avoid circular issues when run as background task
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from ..settings import settings
    from ..db.session import Base

    # Setup temporary database session for the background task
    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    db = SessionLocal()
    try:
        # Retrieve the scan run record
        run = db.query(models.PortScanRun).filter(models.PortScanRun.id == run_id).first()
        if not run:
            return
            
        # Execute the actual network scan
        port_states = await scan_ports(run.target, TOP_PORTS, timeout=settings.scan_timeout_sec)
        open_ports = [p for p,s in port_states.items() if s == "open"]
        
        # Process and store findings for each port
        for p, st in port_states.items():
            rs = score_port(p, st)
            lvl = level(rs)
            rec = recommendation_for(p, lvl)
            db.add(models.PortFinding(
                scan_id=run.id, 
                port=p, 
                proto="tcp", 
                state=st, 
                service=None,
                risk_score=rs, 
                risk_level=lvl, 
                recommendation=rec
            ))
            
        # Update run summary and mark as done
        run.summary = {"open_ports": open_ports, "count_open": len(open_ports)}
        run.status = "done"
        run.ended_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        # Handle failures and record the error message
        run = db.query(models.PortScanRun).filter(models.PortScanRun.id == run_id).first()
        if run:
            run.status = "failed"
            run.ended_at = datetime.now(timezone.utc)
            run.summary = {"error": str(e)}
            db.commit()
    finally:
        db.close()

@router.post("", response_model=ScanRunOut)
async def start_scan(payload: ScanRequest, background: BackgroundTasks, db: Session = Depends(get_db), _=Depends(require_role("admin","analyst"))):
    """
    Initiate a new port scan run for a target.
    
    The scan executes in the background.
    """
    # Create the initial run record
    run = models.PortScanRun(client_id=payload.client_id, target=payload.target)
    db.add(run)
    db.commit()
    db.refresh(run)

    # Schedule the background task
    from ..settings import settings
    background.add_task(_run_scan, settings.database_url, run.id)
    return run

@router.get("", response_model=list[ScanRunOut])
def list_scans(limit: int = 50, db: Session = Depends(get_db), _=Depends(require_role("admin","analyst"))):
    """
    List historical and active scan runs.
    """
    return db.query(models.PortScanRun).order_by(models.PortScanRun.started_at.desc()).limit(limit).all()

@router.get("/{scan_id}/findings", response_model=list[FindingOut])
def findings(scan_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin","analyst"))):
    """
    Retrieve specific findings for a completed scan run.
    """
    return (db.query(models.PortFinding).filter(models.PortFinding.scan_id == scan_id).order_by(models.PortFinding.port.asc()).all())
