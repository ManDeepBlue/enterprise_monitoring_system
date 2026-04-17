"""
FastAPI Dependencies
--------------------
This module defines common dependencies used across the FastAPI application,
including database session management and user authentication/authorization.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .settings import settings
from .db.session import engine, SessionLocal
from jose import jwt, JWTError
from .security import decode_token
from .db import models

# OAuth2 scheme for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_db():
    """
    Creates a new SQLAlchemy session for a request and ensures 
    it is closed after the request is processed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """
    Validates the JWT token from the request header and retrieves 
     the corresponding user from the database.
    
    Raises:
        HTTPException: 401 if token is invalid, expired, or user is inactive.
    """
    try:
        # Decode and verify the JWT token
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    
    # Fetch user from database
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")
    
    return user

def require_role(*roles: str):
    """
    Dependency factory for implementing role-based access control.
    Returns a dependency function that checks if the authenticated user 
    has one of the required roles.
    
    Example: 
        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    """
    def _inner(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Insufficient permissions"
            )
        return user
    return _inner
