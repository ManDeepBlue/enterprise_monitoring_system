"""
Pydantic schemas for Metric data.
"""
from pydantic import BaseModel
from datetime import datetime

class MetricIn(BaseModel):
    """Schema for incoming metrics from clients."""
    cpu: float
    ram: float
    disk: float
    rx_kbps: float
    tx_kbps: float
    connections: int
    ts: datetime | None = None

class MetricOut(BaseModel):
    """Schema for outputting historical metrics."""
    ts: datetime
    cpu: float
    ram: float
    disk: float
    rx_kbps: float
    tx_kbps: float
    connections: int

    class Config:
        from_attributes = True
