from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    user_id: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=100)
    email: Optional[str] = Field(default="")
    occupation: Optional[str] = Field(default="Salaried Professional")

class UserResponse(BaseModel):
    user_id: str
    name: str
    email: Optional[str] = ""
    occupation: Optional[str] = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
