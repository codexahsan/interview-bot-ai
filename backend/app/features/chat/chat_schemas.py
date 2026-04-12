# backend/app/features/chat/chat_schemas.py

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class SessionResponse(BaseModel):
    id: str
    resume_id: int
    created_at: datetime

    class Config:
        from_attributes = True
