
from pydantic import BaseModel

class SettingOut(BaseModel):
    key: str
    value: dict
    class Config:
        from_attributes = True

class SettingUpsert(BaseModel):
    value: dict
