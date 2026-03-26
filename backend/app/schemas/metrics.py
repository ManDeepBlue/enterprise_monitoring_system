
from pydantic import BaseModel
from datetime import datetime

class MetricIn(BaseModel):
    cpu: float
    ram: float
    disk: float
    rx_kbps: float
    tx_kbps: float
    connections: int
    ts: datetime | None = None

class MetricOut(BaseModel):
    ts: datetime
    cpu: float
    ram: float
    disk: float
    rx_kbps: float
    tx_kbps: float
    connections: int

    class Config:
        from_attributes = True
