
from __future__ import annotations

# Lightweight risk scoring suitable for academic + enterprise demo:
# - Known high-risk ports get higher score
# - Open ports default to risk; filtered/closed lower
HIGH_RISK_PORTS = {21, 23, 3389, 445, 5900}
MED_RISK_PORTS = {22, 80, 443, 139, 389, 3306, 5432}

def score_port(port: int, state: str) -> float:
    state = state.lower()
    if state != "open":
        return 0.5
    if port in HIGH_RISK_PORTS:
        return 8.5
    if port in MED_RISK_PORTS:
        return 5.0
    return 2.5

def level(score: float) -> str:
    if score >= 8: return "high"
    if score >= 5: return "medium"
    if score >= 2: return "low"
    return "info"

def recommendation_for(port: int, lvl: str) -> str:
    if lvl == "high":
        return f"Restrict access to port {port} via firewall/VPN, enforce strong auth, and review exposed services."
    if lvl == "medium":
        return f"Validate necessity of port {port}, apply least-privilege access rules, and ensure patching."
    if lvl == "low":
        return f"Monitor port {port} exposure and confirm service hardening and patch status."
    return "No immediate action required."
