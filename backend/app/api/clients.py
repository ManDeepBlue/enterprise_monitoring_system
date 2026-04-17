"""
API endpoints for managing monitoring clients (agents).
Provides functionality to list, register, and delete clients.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import secrets
from ..deps import get_db, require_role
from ..db import models
from ..schemas.clients import ClientCreate, ClientOut
from ..schemas.common import Msg
from ..security import hash_password
from .. import audit

router = APIRouter(prefix="/api/clients", tags=["clients"])

@router.get("", response_model=list[ClientOut])
def list_clients(db: Session = Depends(get_db), _=Depends(require_role("admin","analyst","readonly"))):
    """
    List all registered clients.
    
    Accessible by admin, analyst, and readonly roles.
    """
    return db.query(models.Client).order_by(models.Client.id.asc()).all()

@router.post("", response_model=dict)
def create_client(payload: ClientCreate, db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    """
    Register a new client and generate an agent key.
    
    The generated agent key is returned only once. 
    A hashed version is stored in the database for verification.
    Only administrators can create clients.
    """
    # Generate a secure random key for the agent to use for authentication
    agent_key = secrets.token_urlsafe(32)
    
    # Create the client record with the hashed key
    c = models.Client(
        name=payload.name, 
        tags=payload.tags, 
        agent_key_hash=hash_password(agent_key)
    )
    db.add(c)
    db.flush() # Flush to get the generated ID
    db.refresh(c)
    
    # Log the creation action
    audit.log(db, user.email, "create_client", "client", c.id, meta={"name": c.name})
    db.commit()
    
    # Return the raw agent_key to the user (this is the only time it's visible)
    return {"id": c.id, "name": c.name, "agent_key": agent_key}

@router.delete("/{client_id}", response_model=Msg)
def delete_client(client_id: int, db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    """
    Delete a client by ID.
    
    Removes the client record and all associated data via cascading (if configured).
    Only administrators can delete clients.
    """
    c = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not c:
        raise HTTPException(404, "Client not found")
    
    # Log the deletion action
    audit.log(db, user.email, "delete_client", "client", client_id, meta={"name": c.name})
    
    db.delete(c)
    db.commit()
    return Msg(message="Deleted")
