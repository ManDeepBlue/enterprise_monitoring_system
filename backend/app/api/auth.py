from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from ..deps import get_db
from ..db import models
from ..security import verify_password, create_access_token, hash_password
from ..schemas.auth import LoginRequest, TokenResponse
from ..schemas.common import Msg
from ..audit import log as audit_log

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        # log failed attempt
        if user:
            audit_log(db, payload.email, "login_failed", "user", payload.email,
                      ip=request.client.host if request.client else None)
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")
    token = create_access_token(user.email, user.role)
    audit_log(db, user.email, "login", "user", user.email,
              ip=request.client.host if request.client else None,
              meta={"role": user.role})
    db.commit()
    return TokenResponse(access_token=token, role=user.role)

@router.post("/bootstrap-admin", response_model=Msg)
def bootstrap_admin(email: str, password: str, db: Session = Depends(get_db)):
    # Block entirely if any admin user already exists
    any_admin = db.query(models.User).filter(models.User.role == "admin").first()
    if any_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin already exists")
    db.add(models.User(email=email, hashed_password=hash_password(password), role="admin"))
    audit_log(db, email, "bootstrap_admin", "user", email)
    db.commit()
    return Msg(message="Admin created")