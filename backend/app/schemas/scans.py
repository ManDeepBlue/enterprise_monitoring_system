
from pydantic import BaseModel
from datetime import datetime

class ScanRequest(BaseModel):
    client_id: int
    target: str

class ScanRunOut(BaseModel):
    id: int
    client_id: int
    target: str
    started_at: datetime
    ended_at: datetime | None
    status: str
    summary: dict
    class Config:
        from_attributes = True

class FindingOut(BaseModel):
    port: int
    proto: str
    state: str
    service: str | None
    risk_score: float
    risk_level: str
    recommendation: str
    class Config:
        from_attributes = True
