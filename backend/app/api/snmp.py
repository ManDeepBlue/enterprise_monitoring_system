"""
API endpoints for SNMP operations and monitoring.
Allows querying live devices via SNMP and retrieving historical interface status.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from ..deps import get_db, require_role
from ..db import models
from ..services.snmp import fetch_snmp_interfaces
from ..schemas.snmp import SNMPResponse, SNMPInterface, SNMPQuery, SNMPInterfaceStatusOut

router = APIRouter(prefix="/api/snmp", tags=["snmp"])

@router.get("/latest/{device_id}", response_model=List[SNMPInterfaceStatusOut])
def get_latest_snmp(device_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin", "analyst", "readonly"))):
    """
    Retrieve the most recent polled status for each interface of a specific device.
    
    This query uses a subquery to find the maximum timestamp for each unique 
    interface index to ensure only the latest state is returned.
    """
    from sqlalchemy import func
    
    # Subquery to find the latest timestamp per interface_index for the device
    subq = (
        db.query(
            models.SNMPInterfaceStatus.interface_index,
            func.max(models.SNMPInterfaceStatus.ts).label("max_ts")
        )
        .filter(models.SNMPInterfaceStatus.device_id == device_id)
        .group_by(models.SNMPInterfaceStatus.interface_index)
        .subquery()
    )
    
    # Join the main table with the subquery to fetch the full records for those latest timestamps
    q = (
        db.query(models.SNMPInterfaceStatus)
        .join(subq, (models.SNMPInterfaceStatus.interface_index == subq.c.interface_index) & 
                    (models.SNMPInterfaceStatus.ts == subq.c.max_ts))
        .filter(models.SNMPInterfaceStatus.device_id == device_id)
        .order_by(models.SNMPInterfaceStatus.interface_index.asc())
    )
    return q.all()

@router.get("/query", response_model=SNMPResponse)
async def query_snmp(
    host: str = Query(..., description="The host (IP or hostname) of the device"),
    community: str = Query("public", description="The SNMP community string"),
    port: int = Query(161, description="The SNMP port"),
    _=Depends(require_role("admin", "analyst", "readonly"))
):
    """
    Perform a live SNMP query against a target device (GET version).
    
    Fetches interface information including description, status, and traffic counters.
    """
    try:
        interfaces_data = await fetch_snmp_interfaces(host, community, port)
        # Convert dictionary data from service to Pydantic models
        interfaces = [SNMPInterface(**iface) for iface in interfaces_data]
        return SNMPResponse(host=host, interfaces=interfaces)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"SNMP query failed: {str(e)}")

@router.post("/query", response_model=SNMPResponse)
async def query_snmp_post(
    payload: SNMPQuery,
    _=Depends(require_role("admin", "analyst", "readonly"))
):
    """
    Perform a live SNMP query against a target device (POST version).
    
    Accepts connection parameters in the request body.
    """
    try:
        interfaces_data = await fetch_snmp_interfaces(payload.host, payload.community, payload.port)
        interfaces = [SNMPInterface(**iface) for iface in interfaces_data]
        return SNMPResponse(host=payload.host, interfaces=interfaces)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"SNMP query failed: {str(e)}")
