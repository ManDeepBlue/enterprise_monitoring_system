
from pydantic import BaseModel, Field
from datetime import datetime

class DeviceBase(BaseModel):
    client_id: int
    name: str
    device_type: str
    host: str
    is_enabled: bool = True
    snmp_enabled: bool = False
    snmp_community: str = "public"
    snmp_port: int = 161

class DeviceCreate(DeviceBase):
    name: str = Field(..., min_length=1, max_length=255)
    device_type: str = Field(..., min_length=1, max_length=50)
    host: str = Field(..., pattern=r"^[a-zA-Z0-9\.-]+$")

class DeviceOut(DeviceBase):
    id: int
    class Config:
        from_attributes = True

class DeviceCheckOut(BaseModel):
    device_id: int
    device_name: str | None = None
    ts: datetime
    reachable: bool
    latency_ms: float | None
    class Config:
        from_attributes = True
