from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from uuid import UUID

from app.repositories.base import SQLAlchemyRepository
from app.models.user import User
from app.core.exceptions import UserNotFoundException, UserAlreadyExistsException


class UserRepository(SQLAlchemyRepository[User]):
    """User repository for user-related database operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email_and_active(self, email: str) -> Optional[User]:
        """Get active user by email address."""
        result = await self.session.execute(
            select(User).where(
                and_(User.email == email, User.is_active.is_(True))
            )
        )
        return result.scalar_one_or_none()
    
    async def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        result = await self.session.execute(
            select(User.id).where(User.email == email)
        )
        return result.scalar_one_or_none() is not None
    
    async def get_active_users(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[User]:
        """Get all active users."""
        query = select(User).where(User.is_active.is_(True))
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update_last_login(self, user_id: UUID) -> Optional[User]:
        """Update user's last login timestamp."""
        return await self.update(user_id, last_login_at=func.now())
    
    async def deactivate_user(self, user_id: UUID) -> Optional[User]:
        """Deactivate user account."""
        return await self.update(user_id, is_active=False)
    
    async def activate_user(self, user_id: UUID) -> Optional[User]:
        """Activate user account."""
        return await self.update(user_id, is_active=True)
    
    async def verify_user(self, user_id: UUID) -> Optional[User]:
        """Mark user as verified."""
        return await self.update(user_id, is_verified=True)
    
    async def create_user(self, email: str, password_hash: str, name: str) -> User:
        """Create a new user with validation."""
        if await self.email_exists(email):
            raise UserAlreadyExistsException(email)
        
        return await self.create(
            email=email,
            password_hash=password_hash,
            name=name,
            is_active=True,
            is_verified=False
        )
    
    async def get_user_or_raise(self, user_id: UUID) -> User:
        """Get user by ID or raise exception if not found."""
        user = await self.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(str(user_id))
        return user
    
    async def get_user_by_email_or_raise(self, email: str) -> User:
        """Get user by email or raise exception if not found."""
        user = await self.get_by_email(email)
        if not user:
            raise UserNotFoundException(email)
        return user 