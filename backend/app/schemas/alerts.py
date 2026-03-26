
from pydantic import BaseModel
from datetime import datetime

class AlertOut(BaseModel):
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
    status: str  # ack|closed
