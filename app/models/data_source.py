from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Index
from sqlalchemy.sql import func
from app.database import Base


class DataSource(Base):
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    config_json = Column(JSON, nullable=False)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="idle", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_data_sources_client_id', 'client_id'),
        Index('idx_data_sources_status', 'status'),
    )
