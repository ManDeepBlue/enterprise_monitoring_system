"""
Pydantic schemas for Client management.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any

class ClientCreate(BaseModel):
    """Schema for creating a new client."""
    name: str
    tags: dict[str, Any] = Field(default_factory=dict)

class ClientOut(BaseModel):
    """Schema for outputting client details."""
    id: int
    name: str
    tags: dict
    last_seen: datetime | None
    status: str

    class Config:
        from_attributes = True
