"""
Application Settings & Configuration
------------------------------------
This module defines the configuration schema for the application using Pydantic Settings.
It automatically loads values from environment variables and an optional .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Main settings class for the application.
    Properties are populated from environment variables (case-insensitive) 
    or the specified .env file.
    """
    # Configuration for the Pydantic Settings model
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore" # Ignore extra env vars not defined here
    )

    # General App Info
    app_name: str = "Enterprise Network Monitoring & Productivity System"
    environment: str = "dev"

    # Database & Security (Required fields via Field(...))
    database_url: str = Field(..., alias="DATABASE_URL")
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60

    # CORS configuration (comma-separated origins)
    allow_origins: str = "*"

    # Monitoring & Background Job Intervals
    default_monitor_interval_sec: int = 5
    default_device_check_interval_sec: int = 10
    default_alert_eval_interval_sec: int = 5

    # Port Scanning Configuration
    scan_timeout_sec: int = 2
    scan_top_ports: int = 200

    # Email / SMTP Settings for Alerts
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    alert_email_to: str = ""


# Instantiate the settings object to be imported by other modules
settings = Settings()
