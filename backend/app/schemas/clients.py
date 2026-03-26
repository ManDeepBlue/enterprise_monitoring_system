
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any

class ClientCreate(BaseModel):
    name: str
    tags: dict[str, Any] = Field(default_factory=dict)

class ClientOut(BaseModel):
    id: int
    name: str
    tags: dict
    last_seen: datetime | None
    status: str

    class Config:
        from_attributes = True
