"""
SNMP Monitoring Service
-----------------------
Provides functionality to query network devices via SNMP (Simple Network 
Management Protocol) to retrieve interface status, descriptions, and metadata.
"""

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
    Query a remote host for its network interface table using SNMP WALK (GETNEXT).
    
    This function retrieves interface description, admin status, operational 
    status, and alias (if supported by the device). It then processes these 
    values into a human-readable format with inferred failure reasons.
    
    :param host: The target device IP or hostname.
    :param community: The SNMP community string (default: 'public').
    :param port: The target SNMP port (default: 161).
    :return: A list of dictionaries, each containing detailed interface info.
    :raises Exception: On network failure or SNMP errors.
    """
    print(f"Querying SNMP for host: {host} on port: {port}")
    interfaces = {}
    
    snmp_engine = SnmpEngine()
    community_data = CommunityData(community)
    try:
        # Initialize the asynchronous UDP transport.
        transport_target = await UdpTransportTarget.create((host, port), timeout=3, retries=1)
    except Exception as e:
        raise Exception(f"Failed to initialize SNMP transport: {str(e)}")

    # Define the base OIDs for the walk (Standard MIB-II and IF-MIB).
    # 1.3.6.1.2.1.2.2.1.2     -> ifDescr (Description)
    # 1.3.6.1.2.1.2.2.1.7     -> ifAdminStatus (Desired state: up/down)
    # 1.3.6.1.2.1.2.2.1.8     -> ifOperStatus (Actual state: up/down)
    # 1.3.6.1.2.1.31.1.1.1.18 -> ifAlias (Interface name/alias)

    base_oids = [
        ObjectIdentity('1.3.6.1.2.1.2.2.1.2'), 
        ObjectIdentity('1.3.6.1.2.1.2.2.1.7'),
        ObjectIdentity('1.3.6.1.2.1.2.2.1.8'),
        ObjectIdentity('1.3.6.1.2.1.31.1.1.1.18'),
    ]

    # Initialize the var-binds list with the starting OIDs.
    var_binds = [ObjectType(oid) for oid in base_oids]

    try:
        while True:
            # Perform a single GETNEXT step for all OIDs in parallel.
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

            # The walker continues until the device returns OIDs outside the base subtree.
            first_oid, first_val = varBindTable[0]
            if not base_oids[0].isPrefixOf(first_oid):
                break
            
            # Extract the unique interface index from the end of the OID.
            index = first_oid[-1]
            
            if index not in interfaces:
                interfaces[index] = {"index": int(index)}
            
            # Map the response values to their respective attributes.
            interfaces[index]["description"] = str(varBindTable[0][1])
            interfaces[index]["admin_status"] = int(varBindTable[1][1])
            interfaces[index]["oper_status"] = int(varBindTable[2][1])
            
            # Handle ifAlias specifically, as some devices may not support this MIB branch.
            alias_oid, alias_val = varBindTable[3]
            if base_oids[3].isPrefixOf(alias_oid):
                interfaces[index]["alias"] = str(alias_val)
            else:
                interfaces[index]["alias"] = ""
                
            # Update var_binds to the last received OIDs for the next iteration.
            var_binds = varBindTable

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e
    
    # Post-process raw SNMP integer values into human-readable statuses.
    results = []
    for idx in sorted(interfaces.keys()):
        iface = interfaces[idx]
        admin = iface.get("admin_status")
        oper = iface.get("oper_status")
        
        # Mapping defined in RFC 2863
        status_map = {
            1: "up", 
            2: "down", 
            3: "testing", 
            4: "unknown", 
            5: "dormant", 
            6: "notPresent", 
            7: "lowerLayerDown"
        }
        
        iface["admin_status_name"] = status_map.get(admin, "unknown")
        iface["oper_status_name"] = status_map.get(oper, "unknown")
        
        # Determine a human-readable reason for the interface state.
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
