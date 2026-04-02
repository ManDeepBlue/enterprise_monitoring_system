from __future__ import annotations
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..db import models
from .email_service import send_alert_email

DEFAULT_THRESHOLDS = {
    "cpu_high": 85.0,
    "ram_high": 85.0,
    "disk_high": 90.0,
    "connections_high": 1000,
    "device_offline": True,
}

def _severity_from_value(value: float, warn: float, crit: float) -> str:
    if value >= crit:
        return "critical"
    if value >= warn:
        return "high"
    return "info"

def eval_metrics(db: Session, thresholds: dict) -> list[models.Alert]:
    alerts: list[models.Alert] = []
    clients = db.query(models.Client).all()

    for c in clients:
        latest = (
            db.query(models.Metric)
            .filter(models.Metric.client_id == c.id)
            .order_by(models.Metric.ts.desc())
            .first()
        )
        if not latest:
            continue

        if latest.cpu >= thresholds.get("cpu_high", 85.0):
            sev = _severity_from_value(latest.cpu, thresholds.get("cpu_high", 85.0), 95.0)
            alerts.append(
                models.Alert(
                    client_id=c.id,
                    severity=sev,
                    alert_type="cpu",
                    message=f"High CPU usage on '{c.name}': {latest.cpu:.1f}% (Threshold: {thresholds.get('cpu_high', 85.0)}%)",
                )
            )

        if latest.ram >= thresholds.get("ram_high", 85.0):
            sev = _severity_from_value(latest.ram, thresholds.get("ram_high", 85.0), 95.0)
            alerts.append(
                models.Alert(
                    client_id=c.id,
                    severity=sev,
                    alert_type="ram",
                    message=f"High RAM usage on '{c.name}': {latest.ram:.1f}% (Threshold: {thresholds.get('ram_high', 85.0)}%)",
                )
            )

        if latest.disk >= thresholds.get("disk_high", 90.0):
            sev = _severity_from_value(latest.disk, thresholds.get("disk_high", 90.0), 98.0)
            alerts.append(
                models.Alert(
                    client_id=c.id,
                    severity=sev,
                    alert_type="disk",
                    message=f"High Disk usage on '{c.name}': {latest.disk:.1f}% (Threshold: {thresholds.get('disk_high', 90.0)}%)",
                )
            )

        if latest.connections >= thresholds.get("connections_high", 1000):
            alerts.append(
                models.Alert(
                    client_id=c.id,
                    severity="medium",
                    alert_type="connections",
                    message=f"High connection count on '{c.name}': {latest.connections} (Threshold: {thresholds.get('connections_high', 1000)})",
                )
            )

    return alerts


def eval_audit_logs(db: Session, thresholds: dict) -> list[models.Alert]:
    """Detect suspicious activity from the audit log trail."""
    alerts: list[models.Alert] = []
    now = datetime.now(timezone.utc)
    lookback = now - timedelta(minutes=10)

    # 1. Brute Force Detection: Multiple failed logins for same email
    failed_logins = (
        db.query(models.AuditLog.actor_email, func.count(models.AuditLog.id).label("count"))
        .filter(models.AuditLog.action == "login_failed")
        .filter(models.AuditLog.ts >= lookback)
        .group_by(models.AuditLog.actor_email)
        .having(func.count(models.AuditLog.id) >= 5)
        .all()
    )

    for email, count in failed_logins:
        # We use client_id=1 as a placeholder for system-wide alerts if no specific client is tied
        # Or better, find an admin client or just use a convention. 
        # For now, let's look for any client or just associate with ID 1 if it exists.
        first_client = db.query(models.Client).first()
        cid = first_client.id if first_client else 1
        alerts.append(
            models.Alert(
                client_id=cid,
                severity="critical",
                alert_type="security_brute_force",
                message=f"Security: {count} failed login attempts for {email} in the last 10 minutes.",
            )
        )

    # 2. Sensitive Actions: Alert on deletions or critical setting changes
    sensitive_actions = ["delete_client", "update_setting", "bootstrap_admin", "delete_user"]
    recent_sensitive = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.action.in_(sensitive_actions))
        .filter(models.AuditLog.ts >= lookback)
        .all()
    )

    for log in recent_sensitive:
        cid = 1
        if log.entity == "client" and log.entity_id.isdigit():
            cid = int(log.entity_id)
        else:
            first_client = db.query(models.Client).first()
            if first_client: cid = first_client.id

        alerts.append(
            models.Alert(
                client_id=cid,
                severity="high",
                alert_type="security_audit",
                message=f"Security: Sensitive action '{log.action}' performed by {log.actor_email} on {log.entity} {log.entity_id}",
            )
        )

    return alerts


async def dedupe_and_persist(db: Session, new_alerts: list[models.Alert], window_sec: int = 60) -> int:
    now = datetime.now(timezone.utc)
    created = 0
    alerts_to_email: list[models.Alert] = []

    for a in new_alerts:
        exists = (
            db.query(models.Alert)
            .filter(models.Alert.client_id == a.client_id)
            .filter(models.Alert.alert_type == a.alert_type)
            .filter(models.Alert.status == "open")
            .filter(models.Alert.ts >= now - timedelta(seconds=window_sec))
            .first()
        )

        if exists:
            continue

        db.add(a)
        alerts_to_email.append(a)
        created += 1

    if created:
        db.commit()

        for a in alerts_to_email:
            # Enrichment: Find recent audit logs for this client to provide context
            context_str = ""
            recent_logs = (
                db.query(models.AuditLog)
                .filter(models.AuditLog.ts >= now - timedelta(minutes=15))
                .order_by(models.AuditLog.ts.desc())
                .limit(5)
                .all()
            )
            if recent_logs:
                context_str = "\nRecent System Activity (Log Trail):\n"
                for l in recent_logs:
                    context_str += f"- {l.ts.strftime('%H:%M:%S')} | {l.actor_email} | {l.action} | {l.entity}\n"

            try:
                await send_alert_email(
                    subject=f"[Enterprise Monitoring] {a.severity.upper()} Alert: {a.alert_type}",
                    body=(
                        f"Alert Details:\n"
                        f"----------------\n"
                        f"Message:  {a.message}\n"
                        f"Severity: {a.severity.upper()}\n"
                        f"Type:     {a.alert_type}\n"
                        f"Time:     {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                        f"{context_str}\n"
                        f"Action Required: Please log in to the dashboard to investigate."
                    ),
                )
            except Exception as e:
                print("Email notification failed:", e)

    return created