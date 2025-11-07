from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_log"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    action = Column(String, nullable=False, index=True)
    endpoint = Column(String, nullable=True)
    method = Column(String, nullable=True)
    
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    request_data = Column(JSON, nullable=True)
    response_status = Column(Integer, nullable=True)
    
    execution_time = Column(Integer, nullable=True)  # milliseconds
    
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="activity_logs")
