"""
Pydantic schemas for Alert data.
"""
from pydantic import BaseModel
from datetime import datetime

class AlertOut(BaseModel):
    """Schema for outputting alert details."""
    id: int
    client_id: int
    ts: datetime
    severity: str
    alert_type: str
    message: str
    status: str
    acknowledged_by: str | None

    class Config:
        from_attributes = True

class AlertAck(BaseModel):
    """Schema for acknowledging or closing an alert."""
    status: str  # ack|closed
