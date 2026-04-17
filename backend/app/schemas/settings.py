"""
Pydantic schemas for system Settings.
"""
from pydantic import BaseModel

class SettingOut(BaseModel):
    """Schema for outputting a setting key-value pair."""
    key: str
    value: dict
    class Config:
        from_attributes = True

class SettingUpsert(BaseModel):
    """Schema for creating or updating a setting value."""
    value: dict
