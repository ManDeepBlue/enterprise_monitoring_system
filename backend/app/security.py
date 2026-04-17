"""
Security & Authentication Utilities
-----------------------------------
This module provides utilities for password hashing using bcrypt and 
JWT (JSON Web Token) creation and validation.
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union

from passlib.context import CryptContext
from jose import jwt, JWTError

# Configuration loading with fallback for robustness
try:
    from .settings import settings
    _SECRET_KEY = settings.jwt_secret
    _ALGORITHM = settings.jwt_algorithm
    _ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_minutes
except Exception:
    import os
    _SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
    _ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
    # Default to 7 days if not configured
    _ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7)))

if not _SECRET_KEY:
    _SECRET_KEY = "change-me-in-production"

# Initialize Passlib CryptContext for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _truncate_password_for_bcrypt(password: Optional[str]) -> str:
    """
    Truncates password bytes to the bcrypt 72-byte limit.
    Bcrypt silently ignores bytes beyond 72, which can lead to security 
    misunderstandings. This function makes the truncation explicit and safe.
    """
    if password is None:
        password = ""
    b = password.encode("utf-8")
    if len(b) > 72:
        b = b[:72]
        # Return as string, ignoring any partial characters at the cut-off
        return b.decode("utf-8", errors="ignore")
    return password


def hash_password(password: str) -> str:
    """Returns a bcrypt hash of the given password."""
    pw = _truncate_password_for_bcrypt(password)
    return pwd_context.hash(pw)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against a hashed one.
    Returns True if they match, False otherwise.
    """
    pw = _truncate_password_for_bcrypt(plain_password)
    try:
        return pwd_context.verify(pw, hashed_password)
    except Exception:
        # Catch errors from malformed hashes
        return False


def create_access_token(
    data: Union[Dict[str, Any], str],
    role: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Generates a signed JWT access token.
    
    Args:
        data: Either a dictionary of claims or the 'sub' (subject) string.
        role: Optional role to include in the payload.
        expires_delta: Optional custom expiration time.
        
    Returns:
        Encoded JWT token as a string.
    """
    # If user passed a dict, use it as base for payload
    if isinstance(data, dict):
        to_encode = data.copy()
    else:
        # Treat `data` as the subject (usually email or user ID)
        to_encode = {"sub": data}
        if role:
            to_encode["role"] = role

    # Set expiration time
    if expires_delta is None:
        expires_delta = timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    
    # Encode and sign the JWT
    token = jwt.encode(to_encode, _SECRET_KEY, algorithm=_ALGORITHM)
    return token


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodes and verifies a JWT token using the configured secret key.
    
    Raises:
        jose.JWTError: If the token is expired, invalid, or incorrectly signed.
    """
    payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
    return payload


def get_user_id_from_token(token: str) -> Optional[str]:
    """
    Extracts the 'sub' (subject) from a token without raising exceptions.
    Returns None if decoding fails.
    """
    try:
        payload = decode_token(token)
    except JWTError:
        return None
    return payload.get("sub")


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
    "get_user_id_from_token",
]
