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
    return db.query(models.Client).order_by(models.Client.id.asc()).all()

@router.post("", response_model=dict)
def create_client(payload: ClientCreate, db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    agent_key = secrets.token_urlsafe(32)
    c = models.Client(name=payload.name, tags=payload.tags, agent_key_hash=hash_password(agent_key))
    db.add(c); db.flush(); db.refresh(c)
    audit.log(db, user.email, "create_client", "client", c.id, meta={"name": c.name})
    db.commit()
    return {"id": c.id, "name": c.name, "agent_key": agent_key}

@router.delete("/{client_id}", response_model=Msg)
def delete_client(client_id: int, db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    c = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not c:
        raise HTTPException(404, "Client not found")
    audit.log(db, user.email, "delete_client", "client", client_id, meta={"name": c.name})
    db.delete(c); db.commit()
    return Msg(message="Deleted")