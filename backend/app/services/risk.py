"""
Risk Assessment Service
-----------------------
Calculates risk scores and provides mitigation recommendations based on 
port scanning results and known service vulnerabilities.
"""

from __future__ import annotations

# Port lists categorized by their common exposure risks.
# High-risk ports (e.g., FTP, Telnet, RDP) are historically prone to exploitation.
HIGH_RISK_PORTS = {21, 23, 3389, 445, 5900}
# Medium-risk ports are commonly used but should still be monitored.
MED_RISK_PORTS = {22, 80, 443, 139, 389, 3306, 5432}

def score_port(port: int, state: str) -> float:
    """
    Calculate a numerical risk score for a given port and its connection state.
    
    A higher score indicates a greater security risk.
    
    :param port: The TCP/UDP port number.
    :param state: The scanned state (e.g., 'open', 'closed', 'filtered').
    :return: A float value representing the risk score (0.0 to 10.0 range).
    """
    state = state.lower()
    # Filtered/closed ports represent a lower immediate risk.
    if state != "open":
        return 0.5
    
    # Assign higher scores based on the severity category of the open port.
    if port in HIGH_RISK_PORTS:
        return 8.5
    if port in MED_RISK_PORTS:
        return 5.0
    
    # Default score for any other open port.
    return 2.5

def level(score: float) -> str:
    """
    Map a numerical risk score to a qualitative risk level.
    
    :param score: The calculated risk score.
    :return: A string ('high', 'medium', 'low', or 'info').
    """
    if score >= 8: return "high"
    if score >= 5: return "medium"
    if score >= 2: return "low"
    return "info"

def recommendation_for(port: int, lvl: str) -> str:
    """
    Provide actionable mitigation advice based on the identified risk level.
    
    :param port: The target port number.
    :param lvl: The qualitative risk level.
    :return: A human-readable recommendation string.
    """
    if lvl == "high":
        return (f"Restrict access to port {port} via firewall/VPN immediately. "
                "Enforce strong authentication and review the service for exposure.")
    if lvl == "medium":
        return (f"Validate the business necessity of port {port}. "
                "Apply least-privilege access rules and ensure the service is patched.")
    if lvl == "low":
        return (f"Monitor the exposure of port {port} and confirm service hardening.")
    
    return "No immediate action required, but ensure routine monitoring remains active."
