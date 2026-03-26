from __future__ import annotations
from datetime import datetime, timedelta, timezone
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
                    message=f"CPU usage {latest.cpu:.1f}% exceeded threshold",
                )
            )

        if latest.ram >= thresholds.get("ram_high", 85.0):
            sev = _severity_from_value(latest.ram, thresholds.get("ram_high", 85.0), 95.0)
            alerts.append(
                models.Alert(
                    client_id=c.id,
                    severity=sev,
                    alert_type="ram",
                    message=f"RAM usage {latest.ram:.1f}% exceeded threshold",
                )
            )

        if latest.disk >= thresholds.get("disk_high", 90.0):
            sev = _severity_from_value(latest.disk, thresholds.get("disk_high", 90.0), 98.0)
            alerts.append(
                models.Alert(
                    client_id=c.id,
                    severity=sev,
                    alert_type="disk",
                    message=f"Disk usage {latest.disk:.1f}% exceeded threshold",
                )
            )

        if latest.connections >= thresholds.get("connections_high", 1000):
            alerts.append(
                models.Alert(
                    client_id=c.id,
                    severity="medium",
                    alert_type="connections",
                    message=f"Connections {latest.connections} exceeded threshold",
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
            try:
                await send_alert_email(
                    subject=f"[Enterprise Monitoring] {a.severity.upper()} alert",
                    body=(
                        f"Alert triggered\n\n"
                        f"Client ID: {a.client_id}\n"
                        f"Type: {a.alert_type}\n"
                        f"Severity: {a.severity}\n"
                        f"Message: {a.message}\n"
                    ),
                )
            except Exception as e:
                print("Email notification failed:", e)

    return created