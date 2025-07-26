from sqlalchemy import Column, String, Boolean, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import pytz

from app.core.database import Base
from app.core.config import settings


class User(Base):
    """User model for authentication and user management."""
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User identification
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    
    # Authentication
    password_hash = Column(String(255), nullable=False)
    
    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_users_email_active', 'email', 'is_active'),
        Index('idx_users_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', name='{self.name}')>"
    
    @property
    def created_at_kst(self) -> datetime:
        """Get created_at in KST timezone."""
        if self.created_at:
            return self.created_at.astimezone(pytz.timezone(settings.timezone))
        return None
    
    @property
    def updated_at_kst(self) -> datetime:
        """Get updated_at in KST timezone."""
        if self.updated_at:
            return self.updated_at.astimezone(pytz.timezone(settings.timezone))
        return None
    
    @property
    def last_login_at_kst(self) -> datetime:
        """Get last_login_at in KST timezone."""
        if self.last_login_at:
            return self.last_login_at.astimezone(pytz.timezone(settings.timezone))
        return None
    
    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login_at = func.now()
    
    def to_dict(self, include_password: bool = False) -> dict:
        """Convert user to dictionary representation."""
        data = {
            "id": str(self.id),
            "email": self.email,
            "name": self.name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "last_login_at": self.last_login_at_kst.isoformat() if self.last_login_at_kst else None,
            "created_at": self.created_at_kst.isoformat() if self.created_at_kst else None,
            "updated_at": self.updated_at_kst.isoformat() if self.updated_at_kst else None,
        }
        
        if include_password:
            data["password_hash"] = self.password_hash
            
        return data 