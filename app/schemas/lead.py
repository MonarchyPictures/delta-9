from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class LeadResponse(BaseModel):
    id: uuid.UUID
    title: Optional[str]
    content: Optional[str]
    source: Optional[str]
    url: Optional[str]
    query: Optional[str]
    location: Optional[str]
    confidence: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True
