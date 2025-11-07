from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ClientBase(BaseModel):
    name: str
    industry: Optional[str] = None
    description: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ClientResponse(ClientBase):
    id: int
    schema_name: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
