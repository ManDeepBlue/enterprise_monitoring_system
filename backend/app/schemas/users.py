"""
Pydantic schemas for User management.
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    """Base schema for user data."""
    email: EmailStr
    role: str = "readonly"  # admin|analyst|readonly
    is_active: bool = True

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str

class UserUpdate(BaseModel):
    """Schema for updating an existing user."""
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserOut(UserBase):
    """Schema for outputting user details."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
