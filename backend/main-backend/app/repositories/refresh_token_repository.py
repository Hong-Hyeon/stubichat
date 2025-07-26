from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from uuid import UUID
from datetime import datetime

from app.repositories.base import SQLAlchemyRepository
from app.models.refresh_token import RefreshToken
from app.core.exceptions import InvalidTokenException, ExpiredTokenException, RevokedTokenException


class RefreshTokenRepository(SQLAlchemyRepository[RefreshToken]):
    """Refresh token repository for token-related database operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, RefreshToken)
    
    async def get_by_token_hash(self, token_hash: str) -> Optional[RefreshToken]:
        """Get refresh token by token hash."""
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()
    
    async def get_valid_token(self, token_hash: str) -> Optional[RefreshToken]:
        """Get valid (non-revoked, non-expired) refresh token."""
        result = await self.session.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.is_revoked.is_(False),
                    RefreshToken.expires_at > func.now()
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_tokens_by_user_id(self, user_id: UUID) -> List[RefreshToken]:
        """Get all refresh tokens for a user."""
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.user_id == user_id)
        )
        return result.scalars().all()
    
    async def get_active_tokens_by_user_id(self, user_id: UUID) -> List[RefreshToken]:
        """Get all active (non-revoked, non-expired) refresh tokens for a user."""
        result = await self.session.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.is_revoked.is_(False),
                    RefreshToken.expires_at > func.now()
                )
            )
        )
        return result.scalars().all()
    
    async def revoke_token(self, token_hash: str) -> bool:
        """Revoke a refresh token."""
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        token = result.scalar_one_or_none()
        
        if token:
            token.revoke()
            await self.session.commit()
            return True
        return False
    
    async def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """Revoke all refresh tokens for a user."""
        result = await self.session.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.is_revoked.is_(False)
                )
            )
        )
        tokens = result.scalars().all()
        
        for token in tokens:
            token.revoke()
        
        await self.session.commit()
        return len(tokens)
    
    async def cleanup_expired_tokens(self) -> int:
        """Delete expired refresh tokens."""
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.expires_at < func.now())
        )
        expired_tokens = result.scalars().all()
        
        for token in expired_tokens:
            await self.session.delete(token)
        
        await self.session.commit()
        return len(expired_tokens)
    
    async def create_token(self, user_id: UUID, token_hash: str, expires_at: datetime) -> RefreshToken:
        """Create a new refresh token."""
        return await self.create(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False
        )
    
    async def validate_token(self, token_hash: str) -> RefreshToken:
        """Validate a refresh token and return it if valid."""
        token = await self.get_valid_token(token_hash)
        
        if not token:
            # Check if token exists but is invalid
            existing_token = await self.get_by_token_hash(token_hash)
            if existing_token:
                if existing_token.is_revoked:
                    raise RevokedTokenException("refresh token")
                elif existing_token.is_expired():
                    raise ExpiredTokenException("refresh token")
            
            raise InvalidTokenException("refresh token")
        
        return token 