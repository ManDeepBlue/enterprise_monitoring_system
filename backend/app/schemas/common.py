"""
Common shared Pydantic schemas.
"""
from pydantic import BaseModel

class Msg(BaseModel):
    """Generic message response schema."""
    message: str
