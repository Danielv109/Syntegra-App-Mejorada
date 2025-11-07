from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class DataSourceCreate(BaseModel):
    client_id: int
    name: str
    type: str
    config_json: Dict[str, Any]


class DataSourceResponse(BaseModel):
    id: int
    client_id: int
    name: str
    type: str
    config_json: Dict[str, Any]
    last_run_at: Optional[datetime] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ConnectorRunResponse(BaseModel):
    message: str
    task_id: str
    source_id: int
