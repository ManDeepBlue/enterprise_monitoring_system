from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Enterprise Network Monitoring & Productivity System"
    environment: str = "dev"

    database_url: str = Field(..., alias="DATABASE_URL")
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60

    allow_origins: str = "*"

    # Monitoring defaults
    default_monitor_interval_sec: int = 5
    default_device_check_interval_sec: int = 10
    default_alert_eval_interval_sec: int = 5

    # Port scanning
    scan_timeout_sec: int = 2
    scan_top_ports: int = 200

    # EMAIL SETTINGS (ADD INSIDE CLASS)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    alert_email_to: str = ""


settings = Settings()