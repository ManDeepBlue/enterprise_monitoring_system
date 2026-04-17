"""
Pydantic schemas for SNMP data and queries.
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SNMPInterface(BaseModel):
    """Schema representing a single network interface retrieved via live SNMP query."""
    index: int
    description: str
    alias: Optional[str] = ""
    admin_status: int
    oper_status: int
    admin_status_name: str
    oper_status_name: str
    reason: str

class SNMPResponse(BaseModel):
    """Schema for a live SNMP query response."""
    host: str
    interfaces: List[SNMPInterface]

class SNMPQuery(BaseModel):
    """Schema for SNMP query connection parameters."""
    host: str
    community: str = "public"
    port: int = 161

class SNMPInterfaceStatusOut(BaseModel):
    """Schema for outputting historical SNMP interface status records."""
    ts: datetime
    interface_index: int
    description: str
    alias: Optional[str] = ""
    admin_status: int
    oper_status: int
    reason: str
    class Config:
        from_attributes = True
