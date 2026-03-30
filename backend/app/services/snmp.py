
from pysnmp.hlapi.asyncio import (
    SnmpEngine, 
    CommunityData, 
    UdpTransportTarget, 
    ContextData, 
    ObjectType, 
    ObjectIdentity,
    next_cmd
)
import asyncio

async def fetch_snmp_interfaces(host: str, community: str = 'public', port: int = 161):
    """
    Fetches interface information using SNMP walk.
    Returns a list of dictionaries with interface details.
    """
    print(f"Querying SNMP for host: {host} on port: {port}")
    interfaces = {}
    
    snmp_engine = SnmpEngine()
    community_data = CommunityData(community)
    try:
        transport_target = await UdpTransportTarget.create((host, port), timeout=3, retries=1)
    except Exception as e:
        raise Exception(f"Failed to initialize SNMP transport: {str(e)}")

    # Base OIDs for the walk
    # ifDescr: 1.3.6.1.2.1.2.2.1.2
    # ifAdminStatus: 1.3.6.1.2.1.2.2.1.7
    # ifOperStatus: 1.3.6.1.2.1.2.2.1.8
    # ifAlias: 1.3.6.1.2.1.31.1.1.1.18

    base_oids = [
        ObjectIdentity('1.3.6.1.2.1.2.2.1.2'), # ifDescr
        ObjectIdentity('1.3.6.1.2.1.2.2.1.7'), # ifAdminStatus
        ObjectIdentity('1.3.6.1.2.1.2.2.1.8'), # ifOperStatus
        ObjectIdentity('1.3.6.1.2.1.31.1.1.1.18'), # ifAlias
    ]

    # Current var-binds for the walk, initialized with the base OIDs
    var_binds = [ObjectType(oid) for oid in base_oids]

    try:
        while True:
            # Perform a single GETNEXT/GETBULK step
            try:
                errorIndication, errorStatus, errorIndex, varBindTable = await next_cmd(
                    snmp_engine,
                    community_data,
                    transport_target,
                    ContextData(),
                    *var_binds
                )
            except Exception as e:
                 raise Exception(f"SNMP Query Failed: {str(e)}")

            if errorIndication:
                raise Exception(f"Connection Failed: {errorIndication}")            
            if errorStatus:
                raise Exception(f"SNMP Error: {errorStatus.prettyPrint()}")
                
            if not varBindTable:
                break

            # Process the row (one varBind for each requested column)
            # varBindTable in next_cmd (asyncio) is just a list of ObjectTypes for the row
            
            # Check if we've moved beyond the subtree of the first OID (ifDescr)
            # This is the standard "end of walk" condition
            first_oid, first_val = varBindTable[0]
            if not base_oids[0].isPrefixOf(first_oid):
                break
            
            # Extract index from the OID (last component)
            index = first_oid[-1]
            
            if index not in interfaces:
                interfaces[index] = {"index": int(index)}
            
            # Map values based on position in the request
            interfaces[index]["description"] = str(varBindTable[0][1])
            interfaces[index]["admin_status"] = int(varBindTable[1][1])
            interfaces[index]["oper_status"] = int(varBindTable[2][1])
            
            # Handle ifAlias (might be in a different table or missing)
            alias_oid, alias_val = varBindTable[3]
            if base_oids[3].isPrefixOf(alias_oid):
                interfaces[index]["alias"] = str(alias_val)
            else:
                interfaces[index]["alias"] = ""
                
            # Prepare the next step by using the returned OIDs
            var_binds = varBindTable

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e
    
    # Post-process to add human-readable status and reasons
    results = []
    for idx in sorted(interfaces.keys()):
        iface = interfaces[idx]
        admin = iface.get("admin_status")
        oper = iface.get("oper_status")
        
        status_map = {1: "up", 2: "down", 3: "testing", 4: "unknown", 5: "dormant", 6: "notPresent", 7: "lowerLayerDown"}
        
        iface["admin_status_name"] = status_map.get(admin, "unknown")
        iface["oper_status_name"] = status_map.get(oper, "unknown")
        
        # Determine reason if down
        reason = "N/A"
        if oper == 2: # down
            if admin == 2:
                reason = "Administratively Down (Disabled by Admin)"
            elif admin == 1:
                reason = "Link Failure / Cable Disconnected"
            else:
                reason = f"Down (Admin Status: {admin})"
        elif oper == 7:
            reason = "Lower Layer Down (Check dependent interface)"
        elif oper == 6:
            reason = "Hardware Not Present"
        elif oper == 1:
            reason = "Healthy"
        else:
            reason = f"Status: {status_map.get(oper, 'unknown')}"
            
        iface["reason"] = reason
        results.append(iface)
        
    return results
