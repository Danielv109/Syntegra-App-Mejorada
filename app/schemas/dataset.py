from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.dataset import DatasetStatus


class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None


class DatasetCreate(DatasetBase):
    pass


class DatasetResponse(DatasetBase):
    id: int
    client_id: int
    file_path: str
    file_type: str
    status: DatasetStatus
    rows_count: Optional[int] = None
    columns_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    uploaded_by: int
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ETLHistoryResponse(BaseModel):
    id: int
    dataset_id: int
    task_id: str
    status: DatasetStatus
    step: Optional[str] = None
    message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
