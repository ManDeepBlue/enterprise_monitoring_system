# app/jobs.py
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
    s = db.query(models.Setting).filter(models.Setting.key == key).first()
    return s.value if s else default

async def _job_alerts():
    db = SessionLocal()
    try:
        from .services.alert_engine import eval_audit_logs
        thresholds = _get_setting(db, "alert_thresholds", DEFAULT_THRESHOLDS)
        
        # Smart Alerting: Check both metrics AND audit trail
        metric_alerts = eval_metrics(db, thresholds)
        audit_alerts = eval_audit_logs(db, thresholds)
        
        all_alerts = metric_alerts + audit_alerts
        
        created = await dedupe_and_persist(db, all_alerts, window_sec=900)
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
            try:
                db.add(models.DeviceCheck(device_id=d.id, device_name=d.name, reachable=ok, latency_ms=ms))
                db.commit()
            except Exception:
                # Device was deleted between the query and the commit — skip it cleanly
                db.rollback()
                logging.warning(f"Skipped device_check for device_id={d.id} (likely deleted mid-job)")
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
                await ws_manager.broadcast("realtime", {"type": "snmp_updated", "device_id": d.id})
            except Exception:
                db.rollback()
                logging.exception(f"Error polling SNMP for device {d.host}")
    except Exception:
        logging.exception("Error in _job_snmp_checks")
    finally:
        db.close()