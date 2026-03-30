
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SNMPInterface(BaseModel):
    index: int
    description: str
    alias: Optional[str] = ""
    admin_status: int
    oper_status: int
    admin_status_name: str
    oper_status_name: str
    reason: str

class SNMPResponse(BaseModel):
    host: str
    interfaces: List[SNMPInterface]

class SNMPQuery(BaseModel):
    host: str
    community: str = "public"
    port: int = 161

class SNMPInterfaceStatusOut(BaseModel):
    ts: datetime
    interface_index: int
    description: str
    alias: Optional[str] = ""
    admin_status: int
    oper_status: int
    reason: str
    class Config:
        from_attributes = True
