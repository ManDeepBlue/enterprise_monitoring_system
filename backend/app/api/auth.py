"""
Authentication API endpoints.
Handles user login, token generation, and initial admin bootstrapping.
"""

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
    """
    Authenticate a user and return a JWT access token.
    
    Validates email and password, checks if account is active, 
    and logs both successful and failed attempts to the audit log.
    """
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    
    # Verify user exists and password is correct
    if not user or not verify_password(payload.password, user.hashed_password):
        # Log failed attempt for existing users for security monitoring
        if user:
            audit_log(db, payload.email, "login_failed", "user", payload.email,
                      ip=request.client.host if request.client else None)
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    # Check if user account is disabled
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")
    
    # Generate JWT token with user identity and role
    token = create_access_token(user.email, user.role)
    
    # Log successful login
    audit_log(db, user.email, "login", "user", user.email,
              ip=request.client.host if request.client else None,
              meta={"role": user.role})
    db.commit()
    
    return TokenResponse(access_token=token, role=user.role)

@router.post("/bootstrap-admin", response_model=Msg)
def bootstrap_admin(email: str, password: str, db: Session = Depends(get_db)):
    """
    Create the first administrator user.
    
    This endpoint is only available if no admin user exists in the database.
    Used for initial system setup.
    """
    # Safety check: Block if any admin user already exists
    any_admin = db.query(models.User).filter(models.User.role == "admin").first()
    if any_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin already exists")
    
    # Create the new admin user
    db.add(models.User(email=email, hashed_password=hash_password(password), role="admin"))
    audit_log(db, email, "bootstrap_admin", "user", email)
    db.commit()
    
    return Msg(message="Admin created")
