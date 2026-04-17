"""
Pydantic schemas for Security Scans.
"""
from pydantic import BaseModel
from datetime import datetime

class ScanRequest(BaseModel):
    """Schema for requesting a new security scan."""
    client_id: int
    target: str

class ScanRunOut(BaseModel):
    """Schema for outputting scan run metadata."""
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
    """Schema for outputting specific port findings from a scan."""
    port: int
    proto: str
    state: str
    service: str | None
    risk_score: float
    risk_level: str
    recommendation: str
    class Config:
        from_attributes = True
