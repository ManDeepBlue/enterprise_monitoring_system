"""
Database models for the Enterprise Monitoring System.
Defines the schema for users, clients, metrics, devices, alerts, and security findings.
Uses SQLAlchemy 2.0 style mapped classes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .session import Base

def _utcnow() -> datetime:
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)

class User(Base):
    """
    User model for system authentication and authorization.
    
    Roles: admin, analyst, readonly.
    """
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="admin", nullable=False)  # admin|analyst|readonly
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

class Client(Base):
    """
    Client model representing a monitored agent/endpoint.
    
    Tracks identity, tags, and overall status.
    """
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    agent_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    tags: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    metrics = relationship("Metric", back_populates="client", cascade="all,delete-orphan")
    web_activity = relationship("WebActivity", back_populates="client", cascade="all,delete-orphan")

class Metric(Base):
    """
    Performance metrics collected from clients.
    
    Includes CPU, RAM, Disk usage, and network traffic.
    """
    __tablename__ = "metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True, nullable=False)
    cpu: Mapped[float] = mapped_column(Float, nullable=False)
    ram: Mapped[float] = mapped_column(Float, nullable=False)
    disk: Mapped[float] = mapped_column(Float, nullable=False)
    rx_kbps: Mapped[float] = mapped_column(Float, nullable=False)
    tx_kbps: Mapped[float] = mapped_column(Float, nullable=False)
    connections: Mapped[int] = mapped_column(Integer, nullable=False)

    client = relationship("Client", back_populates="metrics")

# Index for fast retrieval of historical metrics per client
Index("ix_metrics_client_ts", Metric.client_id, Metric.ts)

class Device(Base):
    """
    Network devices managed for SNMP monitoring and reachability checks.
    """
    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    snmp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    snmp_community: Mapped[str] = mapped_column(String(255), default="public", nullable=False)
    snmp_port: Mapped[int] = mapped_column(Integer, default=161, nullable=False)
    
    checks: Mapped[list["DeviceCheck"]] = relationship("DeviceCheck", back_populates="device", cascade="all, delete-orphan")

class SNMPInterfaceStatus(Base):
    """
    Status of specific network interfaces on a device, retrieved via SNMP.
    """
    __tablename__ = "snmp_interface_status"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True, nullable=False)
    interface_index: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    alias: Mapped[str | None] = mapped_column(String(255), nullable=True)
    admin_status: Mapped[int] = mapped_column(Integer, nullable=False)
    oper_status: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)

class DeviceCheck(Base):
    """
    Results of reachability (ICMP ping) checks for devices.
    """
    __tablename__ = "device_checks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True, nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True, nullable=False)
    reachable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    device: Mapped["Device"] = relationship("Device", back_populates="checks")

# Index for fast status history retrieval
Index("ix_device_checks_device_ts", DeviceCheck.device_id, DeviceCheck.ts)

class Alert(Base):
    """
    System-generated alerts based on client activity or device failures.
    """
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False) # critical|warning|info
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False) # open|ack|closed
    acknowledged_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

Index("ix_alerts_client_ts", Alert.client_id, Alert.ts)
Index("ix_alerts_severity_ts", Alert.severity, Alert.ts)

class PortScanRun(Base):
    """
    Metadata for a specific security port scan execution.
    """
    __tablename__ = "port_scan_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False) # running|done|failed
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class PortFinding(Base):
    """
    Specific port discoveries and risk assessments from a scan run.
    """
    __tablename__ = "port_findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("port_scan_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    proto: Mapped[str] = mapped_column(String(8), default="tcp", nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    service: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    recommendation: Mapped[str] = mapped_column(String(512), nullable=False)

Index("ix_findings_scan_port", PortFinding.scan_id, PortFinding.port)

class WebActivity(Base):
    """
    Categorized web domains visited by users on a client endpoint.
    """
    __tablename__ = "web_activity"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    user_label: Mapped[str] = mapped_column(String(255), default="default", nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)

    client = relationship("Client", back_populates="web_activity")

Index("ix_web_client_ts", WebActivity.client_id, WebActivity.ts)
Index("ix_web_category_ts", WebActivity.category, WebActivity.ts)

class Setting(Base):
    """
    General system settings stored as key-value pairs.
    """
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)

class AuditLog(Base):
    """
    Record of administrative actions performed in the system.
    """
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True, nullable=False)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
