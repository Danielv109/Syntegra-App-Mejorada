from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class DatasetStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class Dataset(Base):
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    
    status = Column(Enum(DatasetStatus), default=DatasetStatus.PENDING)
    rows_count = Column(Integer, nullable=True)
    columns_count = Column(Integer, nullable=True)
    
    # Usar nombre diferente en Python pero mapear a "metadata" en BD
    dataset_meta = Column("metadata", JSON, nullable=True)
    
    # O alternativamente usar declared_attr para evitar conflictos
    # @declared_attr
    # def meta_info(cls):
    #     return Column("metadata", JSON, nullable=True)
    
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    client = relationship("Client", back_populates="datasets")
    etl_history = relationship("ETLHistory", back_populates="dataset")


class ETLHistory(Base):
    __tablename__ = "etl_history"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    
    task_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(Enum(DatasetStatus), default=DatasetStatus.PENDING)
    
    step = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="etl_history")
