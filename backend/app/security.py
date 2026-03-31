# app/security.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union

from passlib.context import CryptContext
from jose import jwt, JWTError

# Try to read JWT settings from your app.settings if present,
# otherwise fall back to environment defaults.
try:
    from .settings import settings
    _SECRET_KEY = settings.jwt_secret
    _ALGORITHM = settings.jwt_algorithm
    _ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_minutes
except Exception:
    import os
    _SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
    _ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
    _ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7)))

if not _SECRET_KEY:
    _SECRET_KEY = "change-me-in-production"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _truncate_password_for_bcrypt(password: Optional[str]) -> str:
    """Truncate password bytes to bcrypt 72-byte limit; safe decode if needed."""
    if password is None:
        password = ""
    b = password.encode("utf-8")
    if len(b) > 72:
        b = b[:72]
        return b.decode("utf-8", errors="ignore")
    return password


def hash_password(password: str) -> str:
    pw = _truncate_password_for_bcrypt(password)
    return pwd_context.hash(pw)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pw = _truncate_password_for_bcrypt(plain_password)
    try:
        return pwd_context.verify(pw, hashed_password)
    except Exception:
        return False


# ------------------------------------------------------------------
# create_access_token: flexible signature to accept:
#  - a dict payload: create_access_token({"sub": "id", "role": "x"})
#  - or create_access_token(subject, role=None, expires_delta=None)
# ------------------------------------------------------------------
def create_access_token(
    data: Union[Dict[str, Any], str],
    role: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT token.
    Usage variants:
      create_access_token({"sub": "user@example.com", "role": "admin"})
      create_access_token("user@example.com", "admin")
      create_access_token("user@example.com")  # role optional
    """
    # If user passed a dict, keep it
    if isinstance(data, dict):
        to_encode = data.copy()
    else:
        # treat `data` as subject (string)
        sub = data
        to_encode = {"sub": sub}
        if role:
            to_encode["role"] = role

    if expires_delta is None:
        expires_delta = timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, _SECRET_KEY, algorithm=_ALGORITHM)
    return token


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify token. Raises jose.JWTError on failure.
    """
    payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
    return payload


def get_user_id_from_token(token: str) -> Optional[str]:
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