from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import pytz

from app.core.database import Base
from app.core.config import settings


class RefreshToken(Base):
    """Refresh token model for JWT token management."""
    
    __tablename__ = "refresh_tokens"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Token data
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Token metadata
    is_revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="refresh_tokens")
    
    # Indexes
    __table_args__ = (
        Index('idx_refresh_tokens_user_id', 'user_id'),
        Index('idx_refresh_tokens_expires_at', 'expires_at'),
        Index('idx_refresh_tokens_user_revoked', 'user_id', 'is_revoked'),
    )
    
    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"
    
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
    def expires_at_kst(self) -> datetime:
        """Get expires_at in KST timezone."""
        if self.expires_at:
            return self.expires_at.astimezone(pytz.timezone(settings.timezone))
        return None
    
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now(pytz.timezone(settings.timezone)) > self.expires_at_kst
    
    def revoke(self):
        """Revoke the refresh token."""
        self.is_revoked = True
    
    def to_dict(self) -> dict:
        """Convert refresh token to dictionary representation."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "is_revoked": self.is_revoked,
            "expires_at": self.expires_at_kst.isoformat() if self.expires_at_kst else None,
            "created_at": self.created_at_kst.isoformat() if self.created_at_kst else None,
            "updated_at": self.updated_at_kst.isoformat() if self.updated_at_kst else None,
        } 