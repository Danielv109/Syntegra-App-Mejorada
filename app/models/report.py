from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ReportHistory(Base):
    __tablename__ = "reports_history"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    report_type = Column(String, nullable=False)
    report_name = Column(String, nullable=False)
    
    file_path = Column(String, nullable=False)
    
    parameters = Column(JSON, nullable=True)
    scores = Column(JSON, nullable=True)
    final_score = Column(Float, nullable=True)
    
    executive_summary = Column(Text, nullable=True)
    
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    client = relationship("Client", back_populates="reports")
