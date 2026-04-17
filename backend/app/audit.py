"""
Audit Logging Utility
---------------------
Provides a standardized helper function for recording administrative and 
security-related actions within the system.
"""

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
    """
    Records an entry in the audit log.
    
    Args:
        db: Active SQLAlchemy database session.
        actor_email: Email address of the user performing the action.
        action: Short description of the action (e.g., 'CREATE', 'DELETE', 'LOGIN').
        entity: The type of object being acted upon (e.g., 'User', 'Client').
        entity_id: Unique identifier of the entity.
        ip: Optional IP address of the actor.
        meta: Optional dictionary for additional context or details.
        
    Note: 
        This function calls db.flush() but not db.commit(). 
        The caller is responsible for committing the transaction.
    """
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
    # Flush to ensure entity ID is available/validated if needed, 
    # but let caller decide when to finish the transaction.
    db.flush()
