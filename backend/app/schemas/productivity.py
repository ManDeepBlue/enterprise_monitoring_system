from pydantic import BaseModel, field_serializer
from datetime import datetime, timezone

class WebActivityIn(BaseModel):
    user_label: str = "default"
    ts: datetime | None = None
    domain: str
    url_hash: str
    category: str
    duration_seconds: int = 0

class WebActivityOut(BaseModel):
    ts: datetime
    domain: str
    category: str
    duration_seconds: int

    @field_serializer("ts")
    def serialize_ts(self, v: datetime) -> str:
        # Ensure UTC offset is always included so the browser parses correctly
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    class Config:
        from_attributes = True