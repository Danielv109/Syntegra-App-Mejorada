from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN_GLOBAL = "admin_global"
    CLIENTE_ADMIN = "cliente_admin"
    CLIENTE_ANALISTA = "cliente_analista"
    CLIENTE_VISUALIZADOR = "cliente_visualizador"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    
    role = Column(Enum(UserRole), default=UserRole.CLIENTE_VISUALIZADOR, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    client = relationship("Client", back_populates="users")
    activity_logs = relationship("ActivityLog", back_populates="user")
