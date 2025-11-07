from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class GoldDataset(Base):
    __tablename__ = "gold_dataset"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    text = Column(Text, nullable=False)
    predicted_label = Column(String, nullable=True)
    human_label = Column(String, nullable=False)
    
    confidence_score = Column(Integer, nullable=True)
    
    context = Column(JSON, nullable=True)
    
    corrected_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    corrected_at = Column(DateTime(timezone=True), server_default=func.now())
