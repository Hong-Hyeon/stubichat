from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import pytz

from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.services.jwt_service import JWTService
from app.services.password_service import PasswordService
from app.core.config import settings
from app.core.exceptions import (
    InvalidCredentialsException,
    InactiveUserException,
    UserAlreadyExistsException,
    PasswordValidationException
)
from app.schemas.auth import UserRegisterRequest, UserLoginRequest


class AuthService:
    """Service for authentication operations."""
    
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        jwt_service: JWTService,
        password_service: PasswordService
    ):
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository
        self.jwt_service = jwt_service
        self.password_service = password_service
        self.timezone = pytz.timezone(settings.timezone)
    
    async def register_user(self, request: UserRegisterRequest) -> Tuple[dict, dict]:
        """Register a new user."""
        # Validate password
        try:
            self.password_service.validate_password(request.password)
        except PasswordValidationException as e:
            raise e
        
        # Hash password
        password_hash = self.password_service.hash_password(request.password)
        
        # Create user
        user = await self.user_repository.create_user(
            email=request.email,
            password_hash=password_hash,
            name=request.name
        )
        
        # Generate tokens
        access_token = self.jwt_service.create_access_token(
            data={"sub": str(user.id), "email": user.email, "name": user.name}
        )
        refresh_token_jwt = self.jwt_service.create_refresh_token(str(user.id))
        
        # Store refresh token
        refresh_token = self.jwt_service.extract_refresh_token_from_jwt(refresh_token_jwt)
        token_hash = self.jwt_service.get_refresh_token_hash(refresh_token)
        expires_at = self.jwt_service.get_token_expiration(refresh_token_jwt, "refresh")
        
        await self.refresh_token_repository.create_token(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        
        # Update last login
        await self.user_repository.update_last_login(user.id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token_jwt,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60
        }, user.to_dict()
    
    async def login_user(self, request: UserLoginRequest) -> Tuple[dict, dict]:
        """Authenticate and login a user."""
        # Get user by email
        user = await self.user_repository.get_by_email_and_active(request.email)
        if not user:
            raise InvalidCredentialsException()
        
        # Verify password
        if not self.password_service.verify_password(request.password, user.password_hash):
            raise InvalidCredentialsException()
        
        # Check if user is active
        if not user.is_active:
            raise InactiveUserException(user.email)
        
        # Generate tokens
        access_token = self.jwt_service.create_access_token(
            data={"sub": str(user.id), "email": user.email, "name": user.name}
        )
        refresh_token_jwt = self.jwt_service.create_refresh_token(str(user.id))
        
        # Store refresh token
        refresh_token = self.jwt_service.extract_refresh_token_from_jwt(refresh_token_jwt)
        token_hash = self.jwt_service.get_refresh_token_hash(refresh_token)
        expires_at = self.jwt_service.get_token_expiration(refresh_token_jwt, "refresh")
        
        await self.refresh_token_repository.create_token(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        
        # Update last login
        await self.user_repository.update_last_login(user.id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token_jwt,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60
        }, user.to_dict()
    
    async def logout_user(self, user_id: str, refresh_token: str) -> bool:
        """Logout a user by revoking their refresh token."""
        try:
            # Extract and hash the refresh token
            actual_token = self.jwt_service.extract_refresh_token_from_jwt(refresh_token)
            token_hash = self.jwt_service.get_refresh_token_hash(actual_token)
            
            # Revoke the token
            return await self.refresh_token_repository.revoke_token(token_hash)
        except Exception:
            # If token is invalid, consider logout successful
            return True
    
    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh access token using refresh token."""
        try:
            # Verify refresh token
            payload = self.jwt_service.verify_token(refresh_token, "refresh")
            user_id = payload.get("sub")
            
            if not user_id:
                raise InvalidCredentialsException()
            
            # Get user
            user = await self.user_repository.get_user_or_raise(user_id)
            
            if not user.is_active:
                raise InactiveUserException(user.email)
            
            # Verify token exists in database and is not revoked
            actual_token = self.jwt_service.extract_refresh_token_from_jwt(refresh_token)
            token_hash = self.jwt_service.get_refresh_token_hash(actual_token)
            
            await self.refresh_token_repository.validate_token(token_hash)
            
            # Generate new access token
            access_token = self.jwt_service.create_access_token(
                data={"sub": str(user.id), "email": user.email, "name": user.name}
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": settings.access_token_expire_minutes * 60
            }
            
        except Exception:
            raise InvalidCredentialsException()
    
    async def get_current_user(self, token: str) -> dict:
        """Get current user from access token."""
        try:
            # Verify access token
            payload = self.jwt_service.verify_token(token, "access")
            user_id = payload.get("sub")
            
            if not user_id:
                raise InvalidCredentialsException()
            
            # Get user
            user = await self.user_repository.get_user_or_raise(user_id)
            
            if not user.is_active:
                raise InactiveUserException(user.email)
            
            return user.to_dict()
            
        except Exception:
            raise InvalidCredentialsException()
    
    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all refresh tokens for a user."""
        return await self.refresh_token_repository.revoke_all_user_tokens(user_id)
    
    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired refresh tokens."""
        return await self.refresh_token_repository.cleanup_expired_tokens() 