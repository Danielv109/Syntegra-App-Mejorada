from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Client(Base):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    schema_name = Column(String, unique=True, nullable=False)
    
    industry = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="client")
    datasets = relationship("Dataset", back_populates="client")
    reports = relationship("ReportHistory", back_populates="client")
    clusters = relationship("Cluster", back_populates="client")
