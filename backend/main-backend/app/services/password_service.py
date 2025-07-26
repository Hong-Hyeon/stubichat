from passlib.context import CryptContext
from app.core.config import settings
from app.core.exceptions import PasswordValidationException


class PasswordService:
    """Service for password hashing and verification."""
    
    def __init__(self):
        # Use argon2 for password hashing (preferred over bcrypt)
        self.pwd_context = CryptContext(
            schemes=["argon2"],
            default="argon2",
            argon2__memory_cost=65536,  # 64MB
            argon2__time_cost=3,        # 3 iterations
            argon2__parallelism=1       # 1 thread
        )
    
    def hash_password(self, password: str) -> str:
        """Hash a password using argon2."""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def validate_password(self, password: str) -> None:
        """Validate password strength."""
        errors = []
        
        if len(password) < settings.password_min_length:
            errors.append(f"Password must be at least {settings.password_min_length} characters long")
        
        if len(password) > settings.password_max_length:
            errors.append(f"Password must be no more than {settings.password_max_length} characters long")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        if errors:
            raise PasswordValidationException(
                "Password validation failed",
                details={"errors": errors}
            ) 