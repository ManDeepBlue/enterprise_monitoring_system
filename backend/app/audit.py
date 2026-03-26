# app/audit.py  –  shared audit logging helper
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .db import models


def log(
    db: Session,
    actor_email: str,
    action: str,
    entity: str,
    entity_id: str = "",
    ip: str | None = None,
    meta: dict | None = None,
):
    """Write one row to audit_log and flush (no commit — caller commits)."""
    entry = models.AuditLog(
        ts=datetime.now(timezone.utc),
        actor_email=actor_email,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        ip=ip,
        meta=meta or {},
    )
    db.add(entry)
    db.flush()