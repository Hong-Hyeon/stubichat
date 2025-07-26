from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.core.config import Settings


class RepositoryFactory(ABC):
    """Abstract factory for creating repository instances."""
    
    @abstractmethod
    def create_user_repository(self, session: AsyncSession) -> UserRepository:
        """Create user repository instance."""
        pass
    
    @abstractmethod
    def create_refresh_token_repository(self, session: AsyncSession) -> RefreshTokenRepository:
        """Create refresh token repository instance."""
        pass


class SQLAlchemyRepositoryFactory(RepositoryFactory):
    """SQLAlchemy implementation of repository factory."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    def create_user_repository(self, session: AsyncSession) -> UserRepository:
        """Create SQLAlchemy user repository instance."""
        return UserRepository(session)
    
    def create_refresh_token_repository(self, session: AsyncSession) -> RefreshTokenRepository:
        """Create SQLAlchemy refresh token repository instance."""
        return RefreshTokenRepository(session)


class InMemoryRepositoryFactory(RepositoryFactory):
    """In-memory implementation of repository factory for testing."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._users = {}
        self._refresh_tokens = {}
    
    def create_user_repository(self, session: AsyncSession) -> UserRepository:
        """Create in-memory user repository instance."""
        # For testing purposes, we'll still use SQLAlchemy repository
        # but with an in-memory SQLite database
        return UserRepository(session)
    
    def create_refresh_token_repository(self, session: AsyncSession) -> RefreshTokenRepository:
        """Create in-memory refresh token repository instance."""
        # For testing purposes, we'll still use SQLAlchemy repository
        # but with an in-memory SQLite database
        return RefreshTokenRepository(session)


def get_repository_factory(settings: Optional[Settings] = None) -> RepositoryFactory:
    """Get repository factory instance."""
    from app.core.config import get_settings
    
    if settings is None:
        settings = get_settings()
    
    # For now, always use SQLAlchemy factory
    # In the future, this could be configurable based on settings
    return SQLAlchemyRepositoryFactory(settings) 