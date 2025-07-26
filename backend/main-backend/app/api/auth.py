from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.database import get_db
from app.core.exceptions import AuthException
from app.factory.auth_service_factory import get_auth_service_factory
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
    AuthResponse,
    ErrorResponse
)
from app.core.config import settings

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Security
security = HTTPBearer()

# Router
router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract user ID from JWT token."""
    from app.services.jwt_service import JWTService
    
    jwt_service = JWTService()
    try:
        return jwt_service.get_user_id_from_token(credentials.credentials, "access")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


@router.exception_handler(RateLimitExceeded)
async def ratelimit_handler(request, exc):
    """Handle rate limit exceeded exceptions."""
    return _rate_limit_exceeded_handler(request, exc)


@router.post("/register", response_model=AuthResponse)
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_window}s")
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
    request_info=Depends(get_remote_address)
):
    """Register a new user."""
    try:
        auth_service_factory = get_auth_service_factory()
        auth_service = auth_service_factory.create_auth_service(db)
        
        tokens, user_data = await auth_service.register_user(request)
        
        return AuthResponse(
            success=True,
            message="User registered successfully",
            data={
                "tokens": tokens,
                "user": user_data
            }
        )
        
    except AuthException as e:
        return AuthResponse(
            success=False,
            message=e.message,
            data={"error_code": e.error_code, "details": e.details}
        )
    except Exception as e:
        return AuthResponse(
            success=False,
            message="Registration failed",
            data={"error": str(e)}
        )


@router.post("/login", response_model=AuthResponse)
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_window}s")
async def login(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
    request_info=Depends(get_remote_address)
):
    """Login user."""
    try:
        auth_service_factory = get_auth_service_factory()
        auth_service = auth_service_factory.create_auth_service(db)
        
        tokens, user_data = await auth_service.login_user(request)
        
        return AuthResponse(
            success=True,
            message="Login successful",
            data={
                "tokens": tokens,
                "user": user_data
            }
        )
        
    except AuthException as e:
        return AuthResponse(
            success=False,
            message=e.message,
            data={"error_code": e.error_code, "details": e.details}
        )
    except Exception as e:
        return AuthResponse(
            success=False,
            message="Login failed",
            data={"error": str(e)}
        )


@router.post("/logout", response_model=AuthResponse)
async def logout(
    refresh_token: RefreshTokenRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Logout user."""
    try:
        auth_service_factory = get_auth_service_factory()
        auth_service = auth_service_factory.create_auth_service(db)
        
        success = await auth_service.logout_user(current_user_id, refresh_token.refresh_token)
        
        if success:
            return AuthResponse(
                success=True,
                message="Logout successful"
            )
        else:
            return AuthResponse(
                success=False,
                message="Logout failed"
            )
        
    except AuthException as e:
        return AuthResponse(
            success=False,
            message=e.message,
            data={"error_code": e.error_code, "details": e.details}
        )
    except Exception as e:
        return AuthResponse(
            success=False,
            message="Logout failed",
            data={"error": str(e)}
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    refresh_token: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token."""
    try:
        auth_service_factory = get_auth_service_factory()
        auth_service = auth_service_factory.create_auth_service(db)
        
        tokens = await auth_service.refresh_access_token(refresh_token.refresh_token)
        
        return AuthResponse(
            success=True,
            message="Token refreshed successfully",
            data={"tokens": tokens}
        )
        
    except AuthException as e:
        return AuthResponse(
            success=False,
            message=e.message,
            data={"error_code": e.error_code, "details": e.details}
        )
    except Exception as e:
        return AuthResponse(
            success=False,
            message="Token refresh failed",
            data={"error": str(e)}
        )


@router.get("/me", response_model=AuthResponse)
async def get_current_user(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get current user information."""
    try:
        auth_service_factory = get_auth_service_factory()
        auth_service = auth_service_factory.create_auth_service(db)
        
        user_data = await auth_service.get_current_user(current_user_id)
        
        return AuthResponse(
            success=True,
            message="User information retrieved successfully",
            data={"user": user_data}
        )
        
    except AuthException as e:
        return AuthResponse(
            success=False,
            message=e.message,
            data={"error_code": e.error_code, "details": e.details}
        )
    except Exception as e:
        return AuthResponse(
            success=False,
            message="Failed to retrieve user information",
            data={"error": str(e)}
        ) 