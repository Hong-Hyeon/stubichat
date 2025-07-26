from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import hashlib
import secrets
import pytz

from app.core.config import settings
from app.core.exceptions import InvalidTokenException, ExpiredTokenException


class JWTService:
    """Service for JWT token operations."""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        self.refresh_token_expire_days = settings.refresh_token_expire_days
        self.timezone = pytz.timezone(settings.timezone)
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create a new access token."""
        to_encode = data.copy()
        expire = datetime.now(self.timezone) + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "access"})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create a new refresh token."""
        # Generate a random token
        token = secrets.token_urlsafe(32)
        
        # Create JWT with refresh token data
        to_encode = {
            "sub": user_id,
            "type": "refresh",
            "token": token,
            "exp": datetime.now(self.timezone) + timedelta(days=self.refresh_token_expire_days)
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != token_type:
                raise InvalidTokenException(f"{token_type} token")
            
            # Check expiration
            exp = payload.get("exp")
            if exp is None:
                raise InvalidTokenException(f"{token_type} token")
            
            exp_datetime = datetime.fromtimestamp(exp, tz=self.timezone)
            if exp_datetime < datetime.now(self.timezone):
                raise ExpiredTokenException(f"{token_type} token")
            
            return payload
            
        except JWTError:
            raise InvalidTokenException(f"{token_type} token")
    
    def get_user_id_from_token(self, token: str, token_type: str = "access") -> str:
        """Extract user ID from token."""
        payload = self.verify_token(token, token_type)
        return payload.get("sub")
    
    def get_refresh_token_hash(self, refresh_token: str) -> str:
        """Generate hash for refresh token storage."""
        return hashlib.sha256(refresh_token.encode()).hexdigest()
    
    def extract_refresh_token_from_jwt(self, refresh_token_jwt: str) -> str:
        """Extract the actual refresh token from JWT."""
        payload = self.verify_token(refresh_token_jwt, "refresh")
        return payload.get("token")
    
    def get_token_expiration(self, token: str, token_type: str = "access") -> datetime:
        """Get token expiration time."""
        payload = self.verify_token(token, token_type)
        exp = payload.get("exp")
        return datetime.fromtimestamp(exp, tz=self.timezone)
    
    def is_token_expired(self, token: str, token_type: str = "access") -> bool:
        """Check if token is expired."""
        try:
            self.verify_token(token, token_type)
            return False
        except ExpiredTokenException:
            return True
        except InvalidTokenException:
            return True 