"""
Pydantic schemas for Productivity (Web Activity) data.
"""
from pydantic import BaseModel, field_serializer
from datetime import datetime, timezone

class WebActivityIn(BaseModel):
    """Schema for incoming web activity data from clients."""
    user_label: str = "default"
    ts: datetime | None = None
    domain: str
    url_hash: str
    category: str

class WebActivityOut(BaseModel):
    """Schema for outputting web activity history."""
    id: int
    ts: datetime
    domain: str
    category: str

    @field_serializer("ts")
    def serialize_ts(self, v: datetime) -> str:
        """Serialize timestamp to ISO format with UTC offset."""
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    class Config:
        from_attributes = True
