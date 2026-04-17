"""
Pydantic schemas for Authentication.
"""
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    """Schema for user login requests."""
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """Schema for authentication token responses."""
    access_token: str
    token_type: str = "bearer"
    role: str
