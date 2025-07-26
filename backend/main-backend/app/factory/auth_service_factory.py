from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import AuthService
from app.services.jwt_service import JWTService
from app.services.password_service import PasswordService
from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.factory.repository_factory import RepositoryFactory
from app.core.config import Settings


class AuthServiceFactory(ABC):
    """Abstract factory for creating authentication service instances."""
    
    @abstractmethod
    def create_auth_service(self, session: AsyncSession) -> AuthService:
        """Create authentication service instance."""
        pass


class SQLAlchemyAuthServiceFactory(AuthServiceFactory):
    """SQLAlchemy implementation of authentication service factory."""
    
    def __init__(self, repository_factory: RepositoryFactory, settings: Settings):
        self.repository_factory = repository_factory
        self.settings = settings
        self._jwt_service: Optional[JWTService] = None
        self._password_service: Optional[PasswordService] = None
    
    @property
    def jwt_service(self) -> JWTService:
        """Get or create JWT service instance."""
        if self._jwt_service is None:
            self._jwt_service = JWTService()
        return self._jwt_service
    
    @property
    def password_service(self) -> PasswordService:
        """Get or create password service instance."""
        if self._password_service is None:
            self._password_service = PasswordService()
        return self._password_service
    
    def create_auth_service(self, session: AsyncSession) -> AuthService:
        """Create SQLAlchemy authentication service instance."""
        user_repository = self.repository_factory.create_user_repository(session)
        refresh_token_repository = self.repository_factory.create_refresh_token_repository(session)
        
        return AuthService(
            user_repository=user_repository,
            refresh_token_repository=refresh_token_repository,
            jwt_service=self.jwt_service,
            password_service=self.password_service
        )


class InMemoryAuthServiceFactory(AuthServiceFactory):
    """In-memory implementation of authentication service factory for testing."""
    
    def __init__(self, repository_factory: RepositoryFactory, settings: Settings):
        self.repository_factory = repository_factory
        self.settings = settings
        self._jwt_service: Optional[JWTService] = None
        self._password_service: Optional[PasswordService] = None
    
    @property
    def jwt_service(self) -> JWTService:
        """Get or create JWT service instance."""
        if self._jwt_service is None:
            self._jwt_service = JWTService()
        return self._jwt_service
    
    @property
    def password_service(self) -> PasswordService:
        """Get or create password service instance."""
        if self._password_service is None:
            self._password_service = PasswordService()
        return self._password_service
    
    def create_auth_service(self, session: AsyncSession) -> AuthService:
        """Create in-memory authentication service instance."""
        user_repository = self.repository_factory.create_user_repository(session)
        refresh_token_repository = self.repository_factory.create_refresh_token_repository(session)
        
        return AuthService(
            user_repository=user_repository,
            refresh_token_repository=refresh_token_repository,
            jwt_service=self.jwt_service,
            password_service=self.password_service
        )


def get_auth_service_factory(settings: Optional[Settings] = None) -> AuthServiceFactory:
    """Get authentication service factory instance."""
    from app.core.config import get_settings
    from app.factory.repository_factory import get_repository_factory
    
    if settings is None:
        settings = get_settings()
    
    repository_factory = get_repository_factory(settings)
    
    # For now, always use SQLAlchemy factory
    # In the future, this could be configurable based on settings
    return SQLAlchemyAuthServiceFactory(repository_factory, settings) 