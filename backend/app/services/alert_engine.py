"""
Alert Engine Service
--------------------
This module provides the core logic for evaluating system metrics and audit logs
to generate alerts, deduplicate them, and send notifications.
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..db import models
from .email_service import send_alert_email

# Default thresholds for various system metrics.
# These act as fallbacks if no specific configuration is provided.
DEFAULT_THRESHOLDS = {
    "cpu_high": 85.0,
    "ram_high": 85.0,
    "disk_high": 90.0,
    "connections_high": 1000,
    "device_offline": True,
}

def _severity_from_value(value: float, warn: float, crit: float) -> str:
    """
    Determine the alert severity based on the measured value and threshold boundaries.
    
    :param value: The current metric value.
    :param warn: The warning threshold.
    :param crit: The critical threshold.
    :return: A string representing the severity level ('critical', 'high', or 'info').
    """
    if value >= crit:
        return "critical"
    if value >= warn:
        return "high"
    return "info"

def eval_metrics(db: Session, thresholds: dict) -> list[models.Alert]:
    """
    Evaluate the latest metrics for all clients against the provided thresholds.
    
    This function iterates through all registered clients, fetches their most
    recent metric record, and compares CPU, RAM, Disk, and Connection counts
    against defined limits.
    
    :param db: The database session.
    :param thresholds: A dictionary of metric thresholds.
    :return: A list of newly generated Alert objects (not yet persisted).
    """
    alerts: list[models.Alert] = []
    clients = db.query(models.Client).all()

    for c in clients:
        # Fetch only the single most recent metric for this client.
        latest = (
            db.query(models.Metric)
            .filter(models.Metric.client_id == c.id)
            .order_by(models.Metric.ts.desc())
            .first()
        )
        if not latest:
            continue

        # CPU Usage Check
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

        # RAM Usage Check
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

        # Disk Usage Check
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

        # Active Connections Check
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
    """
    Detect suspicious activity or sensitive operations from the audit log trail.
    
    This analyzes the last 10 minutes of logs for:
    1. Brute force attempts (multiple failed logins).
    2. Sensitive administrative actions (deletions, setting updates).
    
    :param db: The database session.
    :param thresholds: A dictionary of thresholds (unused here but kept for signature consistency).
    :return: A list of newly generated security Alert objects.
    """
    alerts: list[models.Alert] = []
    now = datetime.now(timezone.utc)
    lookback = now - timedelta(minutes=10)

    # 1. Brute Force Detection: Multiple failed logins for same email
    # We group by email and count failures within the lookback window.
    failed_logins = (
        db.query(models.AuditLog.actor_email, func.count(models.AuditLog.id).label("count"))
        .filter(models.AuditLog.action == "login_failed")
        .filter(models.AuditLog.ts >= lookback)
        .group_by(models.AuditLog.actor_email)
        .having(func.count(models.AuditLog.id) >= 5)
        .all()
    )

    for email, count in failed_logins:
        # Security alerts are often system-wide. We associate them with the first client found
        # or ID 1 as a fallback for the dashboard to display them.
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
        # Try to associate the alert with a specific client if mentioned in the log entity.
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
    """
    Prevent alert fatigue by deduping similar alerts and persisting new ones.
    
    If an open alert of the same type and client exists within the 'window_sec' time frame,
    the new alert is discarded. Otherwise, it is saved to the database and an email is sent.
    
    :param db: The database session.
    :param new_alerts: List of candidate Alert objects.
    :param window_sec: The time window in seconds for deduplication.
    :return: The number of new alerts actually created.
    """
    now = datetime.now(timezone.utc)
    created = 0
    alerts_to_email: list[models.Alert] = []

    for a in new_alerts:
        # Check for existing open alerts of the same type for this client within the time window.
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

        # For each new alert, send an email notification with enriched system context.
        for a in alerts_to_email:
            # Enrichment: Find the most recent audit logs to provide context in the email.
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
                # Log the error but don't crash the background job.
                print("Email notification failed:", e)

    return created