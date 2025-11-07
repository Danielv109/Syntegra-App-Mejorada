from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.database import Base


class AnalyticsSummary(Base):
    __tablename__ = "analytics_summary"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    
    date = Column(Date, nullable=False, index=True)
    metric_name = Column(String, nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    
    metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Trend(Base):
    __tablename__ = "trends"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    
    keyword = Column(String, nullable=False, index=True)
    category = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    
    frequency = Column(Integer, nullable=False)
    growth_rate = Column(Float, nullable=True)
    trend_status = Column(String, nullable=False)  # emergente, estable, en descenso
    
    time_period_start = Column(Date, nullable=False)
    time_period_end = Column(Date, nullable=False)
    
    embedding = Column(Vector(384), nullable=True)
    
    metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Cluster(Base):
    __tablename__ = "clusters"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    cluster_id = Column(Integer, nullable=False)
    cluster_name = Column(String, nullable=True)
    
    features_used = Column(JSON, nullable=False)
    centroid = Column(JSON, nullable=True)
    
    size = Column(Integer, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    client = relationship("Client", back_populates="clusters")
