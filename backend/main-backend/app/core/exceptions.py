from typing import Optional, Dict, Any


class AuthException(Exception):
    """Base exception for authentication errors."""
    
    def __init__(self, message: str, error_code: str = "AUTH_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class UserNotFoundException(AuthException):
    """Exception raised when user is not found."""
    
    def __init__(self, email: str):
        super().__init__(
            message=f"User with email '{email}' not found",
            error_code="USER_NOT_FOUND",
            details={"email": email}
        )


class UserAlreadyExistsException(AuthException):
    """Exception raised when user already exists."""
    
    def __init__(self, email: str):
        super().__init__(
            message=f"User with email '{email}' already exists",
            error_code="USER_ALREADY_EXISTS",
            details={"email": email}
        )


class InvalidCredentialsException(AuthException):
    """Exception raised when credentials are invalid."""
    
    def __init__(self):
        super().__init__(
            message="Invalid email or password",
            error_code="INVALID_CREDENTIALS"
        )


class InactiveUserException(AuthException):
    """Exception raised when user account is inactive."""
    
    def __init__(self, email: str):
        super().__init__(
            message=f"User account '{email}' is inactive",
            error_code="INACTIVE_USER",
            details={"email": email}
        )


class InvalidTokenException(AuthException):
    """Exception raised when token is invalid."""
    
    def __init__(self, token_type: str = "token"):
        super().__init__(
            message=f"Invalid {token_type}",
            error_code="INVALID_TOKEN",
            details={"token_type": token_type}
        )


class ExpiredTokenException(AuthException):
    """Exception raised when token is expired."""
    
    def __init__(self, token_type: str = "token"):
        super().__init__(
            message=f"{token_type.capitalize()} has expired",
            error_code="EXPIRED_TOKEN",
            details={"token_type": token_type}
        )


class RevokedTokenException(AuthException):
    """Exception raised when token is revoked."""
    
    def __init__(self, token_type: str = "token"):
        super().__init__(
            message=f"{token_type.capitalize()} has been revoked",
            error_code="REVOKED_TOKEN",
            details={"token_type": token_type}
        )


class PasswordValidationException(AuthException):
    """Exception raised when password validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="PASSWORD_VALIDATION_ERROR",
            details=details
        )


class RateLimitException(AuthException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, action: str, retry_after: int):
        super().__init__(
            message=f"Rate limit exceeded for {action}",
            error_code="RATE_LIMIT_EXCEEDED",
            details={"action": action, "retry_after": retry_after}
        ) 