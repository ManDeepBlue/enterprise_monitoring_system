
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .session import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="admin", nullable=False)  # admin|analyst|readonly
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class Client(Base):
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    agent_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # hashed shared secret for agent auth
    tags: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)  # online/offline/unknown
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    metrics = relationship("Metric", back_populates="client", cascade="all,delete-orphan")
    web_activity = relationship("WebActivity", back_populates="client", cascade="all,delete-orphan")

class Metric(Base):
    __tablename__ = "metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    cpu: Mapped[float] = mapped_column(Float, nullable=False)
    ram: Mapped[float] = mapped_column(Float, nullable=False)
    disk: Mapped[float] = mapped_column(Float, nullable=False)
    rx_kbps: Mapped[float] = mapped_column(Float, nullable=False)
    tx_kbps: Mapped[float] = mapped_column(Float, nullable=False)
    connections: Mapped[int] = mapped_column(Integer, nullable=False)

    client = relationship("Client", back_populates="metrics")

Index("ix_metrics_client_ts", Metric.client_id, Metric.ts)

class Device(Base):
    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)  # router|switch|ap|other
    host: Mapped[str] = mapped_column(String(255), nullable=False)  # ip or hostname
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class DeviceCheck(Base):
    __tablename__ = "device_checks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    reachable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

Index("ix_device_checks_device_ts", DeviceCheck.device_id, DeviceCheck.ts)

class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # info|low|medium|high|critical
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)  # open|ack|closed
    acknowledged_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

Index("ix_alerts_client_ts", Alert.client_id, Alert.ts)
Index("ix_alerts_severity_ts", Alert.severity, Alert.ts)

class PortScanRun(Base):
    __tablename__ = "port_scan_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False)  # running|done|failed
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class PortFinding(Base):
    __tablename__ = "port_findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("port_scan_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    proto: Mapped[str] = mapped_column(String(8), default="tcp", nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)  # open/closed/filtered
    service: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    recommendation: Mapped[str] = mapped_column(String(512), nullable=False)

Index("ix_findings_scan_port", PortFinding.scan_id, PortFinding.port)

class WebActivity(Base):
    __tablename__ = "web_activity"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    user_label: Mapped[str] = mapped_column(String(255), default="default", nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    client = relationship("Client", back_populates="web_activity")

Index("ix_web_client_ts", WebActivity.client_id, WebActivity.ts)
Index("ix_web_category_ts", WebActivity.category, WebActivity.ts)

class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # attribute renamed to `meta` to avoid SQLAlchemy Declarative reserved attribute name
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)

