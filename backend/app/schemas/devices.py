
from pydantic import BaseModel
from datetime import datetime

class DeviceCreate(BaseModel):
    client_id: int
    name: str
    device_type: str
    host: str
    is_enabled: bool = True

class DeviceOut(DeviceCreate):
    id: int
    class Config:
        from_attributes = True

class DeviceCheckOut(BaseModel):
    ts: datetime
    reachable: bool
    latency_ms: float | None
    class Config:
        from_attributes = True
