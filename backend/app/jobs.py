"""
Background Jobs & Schedulers
---------------------------
This module contains the background logic for periodic tasks such as
alert evaluation, client connectivity checks, and network device monitoring.
These functions are typically invoked by a scheduler (e.g., APScheduler).
"""

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from .db import models
from .db.session import SessionLocal
from .ws import ws_manager
from .services.alert_engine import eval_metrics, dedupe_and_persist, DEFAULT_THRESHOLDS
from .services.icmp import ping
from .services.snmp import fetch_snmp_interfaces

def _get_setting(db: Session, key: str, default: dict):
    """
    Helper function to retrieve a JSON setting from the database.
    """
    s = db.query(models.Setting).filter(models.Setting.key == key).first()
    return s.value if s else default

async def _job_alerts():
    """
    Periodic job to evaluate recent metrics and audit logs against 
    configured thresholds and generate alerts if needed.
    """
    db = SessionLocal()
    try:
        from .services.alert_engine import eval_audit_logs
        # Retrieve thresholds from DB or use defaults
        thresholds = _get_setting(db, "alert_thresholds", DEFAULT_THRESHOLDS)
        
        # 1. Evaluate system metrics for anomalies (CPU, RAM, etc.)
        metric_alerts = eval_metrics(db, thresholds)
        # 2. Evaluate audit logs for security concerns (Failed logins, etc.)
        audit_alerts = eval_audit_logs(db, thresholds)
        
        all_alerts = metric_alerts + audit_alerts
        
        # Persist new alerts, avoiding duplicates within a time window
        created = await dedupe_and_persist(db, all_alerts, window_sec=900)
        
        # Notify the dashboard if new alerts were generated
        if created:
            await ws_manager.broadcast("realtime", {"type": "alerts_updated"})
    except Exception:
        logging.exception("Error in _job_alerts")
    finally:
        db.close()

async def _job_mark_offline():
    """
    Periodic job to mark clients as 'offline' if they haven't sent 
    metrics within a certain grace period.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        # Determine how long to wait before marking offline (default 30s)
        interval = _get_setting(db, "monitoring", {"offline_after_sec": 30}).get("offline_after_sec", 30)
        
        for c in db.query(models.Client).all():
            if not c.last_seen: continue
            
            # Normalize timestamp for comparison
            last_seen = c.last_seen.replace(tzinfo=timezone.utc) if c.last_seen.tzinfo is None else c.last_seen
            
            # Check if threshold exceeded
            if (now - last_seen) > timedelta(seconds=interval):
                if c.status != "offline":
                    c.status = "offline"
                    # We could also broadcast this status change
        db.commit()
    except Exception:
        logging.exception("Error in _job_mark_offline")
    finally:
        db.close()

async def _job_device_checks():
    """
    Periodic job to check the reachability and latency of network 
    devices using ICMP (ping).
    """
    db = SessionLocal()
    try:
        # Get ping timeout from settings
        timeout = float(_get_setting(db, "device_checks", {"timeout_sec": 1.0}).get("timeout_sec", 1.0))
        
        # Fetch all enabled devices
        devices_q = db.query(models.Device).filter(models.Device.is_enabled == True).all()
        for d in devices_q:
            # Perform asynchronous ping
            ok, ms = await ping(d.host, timeout=timeout)
            try:
                # Record results
                db.add(models.DeviceCheck(
                    device_id=d.id, 
                    device_name=d.name, 
                    reachable=ok, 
                    latency_ms=ms
                ))
                db.commit()
            except Exception:
                # Handle cases where device might be concurrently deleted
                db.rollback()
                logging.warning(f"Skipped device_check for device_id={d.id} (likely deleted mid-job)")
    except Exception:
        logging.exception("Error in _job_device_checks")
    finally:
        db.close()

async def _job_snmp_checks():
    """
    Periodic job to poll network devices for interface status 
    using the SNMP protocol.
    """
    db = SessionLocal()
    try:
        # Fetch enabled devices that have SNMP enabled
        devices_q = db.query(models.Device).filter(
            models.Device.is_enabled == True, 
            models.Device.snmp_enabled == True
        ).all()
        
        for d in devices_q:
            try:
                # Poll SNMP interface status
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
                # Notify frontend that SNMP data has been updated
                await ws_manager.broadcast("realtime", {"type": "snmp_updated", "device_id": d.id})
            except Exception:
                db.rollback()
                logging.exception(f"Error polling SNMP for device {d.host}")
    except Exception:
        logging.exception("Error in _job_snmp_checks")
    finally:
        db.close()
