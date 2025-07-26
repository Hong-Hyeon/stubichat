"""
Basic tests for the authentication system.
This file demonstrates the core functionality of the user management system.
"""

import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import AsyncSessionLocal, init_db
from app.factory.auth_service_factory import get_auth_service_factory
from app.schemas.auth import UserRegisterRequest, UserLoginRequest
from app.core.exceptions import (
    UserAlreadyExistsException,
    InvalidCredentialsException,
    PasswordValidationException
)


@pytest.fixture
async def db_session():
    """Create a database session for testing."""
    await init_db()
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def auth_service(db_session: AsyncSession):
    """Create an authentication service for testing."""
    auth_service_factory = get_auth_service_factory()
    return auth_service_factory.create_auth_service(db_session)


class TestUserRegistration:
    """Test user registration functionality."""
    
    async def test_register_valid_user(self, auth_service):
        """Test registering a valid user."""
        request = UserRegisterRequest(
            email="test@example.com",
            password="SecurePass123!",
            name="Test User"
        )
        
        tokens, user = await auth_service.register_user(request)
        
        assert tokens is not None
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] == 1800  # 30 minutes
        
        assert user is not None
        assert user["email"] == "test@example.com"
        assert user["name"] == "Test User"
        assert user["is_active"] is True
        assert user["is_verified"] is False
        assert user["id"] is not None
    
    async def test_register_duplicate_user(self, auth_service):
        """Test registering a user with duplicate email."""
        request = UserRegisterRequest(
            email="duplicate@example.com",
            password="SecurePass123!",
            name="Test User"
        )
        
        # Register first user
        await auth_service.register_user(request)
        
        # Try to register duplicate
        with pytest.raises(UserAlreadyExistsException):
            await auth_service.register_user(request)
    
    async def test_register_weak_password(self, auth_service):
        """Test registering with weak password."""
        request = UserRegisterRequest(
            email="weak@example.com",
            password="weak",  # Too weak
            name="Test User"
        )
        
        with pytest.raises(PasswordValidationException):
            await auth_service.register_user(request)


class TestUserLogin:
    """Test user login functionality."""
    
    async def test_login_valid_user(self, auth_service):
        """Test logging in with valid credentials."""
        # First register a user
        register_request = UserRegisterRequest(
            email="login@example.com",
            password="SecurePass123!",
            name="Login User"
        )
        await auth_service.register_user(register_request)
        
        # Then login
        login_request = UserLoginRequest(
            email="login@example.com",
            password="SecurePass123!"
        )
        
        tokens, user = await auth_service.login_user(login_request)
        
        assert tokens is not None
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert user["email"] == "login@example.com"
        assert user["last_login_at"] is not None
    
    async def test_login_invalid_credentials(self, auth_service):
        """Test logging in with invalid credentials."""
        login_request = UserLoginRequest(
            email="nonexistent@example.com",
            password="WrongPass123!"
        )
        
        with pytest.raises(InvalidCredentialsException):
            await auth_service.login_user(login_request)
    
    async def test_login_wrong_password(self, auth_service):
        """Test logging in with wrong password."""
        # First register a user
        register_request = UserRegisterRequest(
            email="wrongpass@example.com",
            password="SecurePass123!",
            name="Wrong Pass User"
        )
        await auth_service.register_user(register_request)
        
        # Then login with wrong password
        login_request = UserLoginRequest(
            email="wrongpass@example.com",
            password="WrongPass123!"
        )
        
        with pytest.raises(InvalidCredentialsException):
            await auth_service.login_user(login_request)


class TestTokenManagement:
    """Test JWT token management."""
    
    async def test_refresh_token(self, auth_service):
        """Test refreshing access token."""
        # First register and login
        register_request = UserRegisterRequest(
            email="refresh@example.com",
            password="SecurePass123!",
            name="Refresh User"
        )
        tokens, user = await auth_service.register_user(register_request)
        
        # Refresh the access token
        new_tokens = await auth_service.refresh_access_token(tokens["refresh_token"])
        
        assert "access_token" in new_tokens
        assert "token_type" in new_tokens
        assert "expires_in" in new_tokens
        assert new_tokens["token_type"] == "bearer"
    
    async def test_logout_user(self, auth_service):
        """Test user logout."""
        # First register and login
        register_request = UserRegisterRequest(
            email="logout@example.com",
            password="SecurePass123!",
            name="Logout User"
        )
        tokens, user = await auth_service.register_user(register_request)
        
        # Logout
        success = await auth_service.logout_user(user["id"], tokens["refresh_token"])
        assert success is True
        
        # Try to refresh with revoked token
        with pytest.raises(InvalidCredentialsException):
            await auth_service.refresh_access_token(tokens["refresh_token"])


class TestUserManagement:
    """Test user management functionality."""
    
    async def test_get_current_user(self, auth_service):
        """Test getting current user information."""
        # First register and login
        register_request = UserRegisterRequest(
            email="current@example.com",
            password="SecurePass123!",
            name="Current User"
        )
        tokens, user = await auth_service.register_user(register_request)
        
        # Get current user from token
        current_user = await auth_service.get_current_user(tokens["access_token"])
        
        assert current_user["id"] == user["id"]
        assert current_user["email"] == user["email"]
        assert current_user["name"] == user["name"]
    
    async def test_revoke_all_user_tokens(self, auth_service):
        """Test revoking all tokens for a user."""
        # First register and login
        register_request = UserRegisterRequest(
            email="revoke@example.com",
            password="SecurePass123!",
            name="Revoke User"
        )
        tokens, user = await auth_service.register_user(register_request)
        
        # Revoke all tokens
        revoked_count = await auth_service.revoke_all_user_tokens(user["id"])
        assert revoked_count >= 1
        
        # Try to refresh with revoked token
        with pytest.raises(InvalidCredentialsException):
            await auth_service.refresh_access_token(tokens["refresh_token"])


# Example usage demonstration
async def demonstrate_auth_system():
    """Demonstrate the complete authentication system workflow."""
    print("🔐 Stubichat Authentication System Demo")
    print("=" * 50)
    
    # Initialize database and service
    await init_db()
    async with AsyncSessionLocal() as session:
        auth_service_factory = get_auth_service_factory()
        auth_service = auth_service_factory.create_auth_service(session)
        
        # 1. Register a new user
        print("\n1. 📝 Registering new user...")
        register_request = UserRegisterRequest(
            email="demo@stubichat.com",
            password="DemoPass123!",
            name="Demo User"
        )
        
        try:
            tokens, user = await auth_service.register_user(register_request)
            print("✅ User registered successfully!")
            print(f"   Email: {user['email']}")
            print(f"   Name: {user['name']}")
            print(f"   User ID: {user['id']}")
            print(f"   Access Token: {tokens['access_token'][:50]}...")
        except Exception as e:
            print(f"❌ Registration failed: {e}")
            return
        
        # 2. Login with the user
        print("\n2. 🔑 Logging in...")
        login_request = UserLoginRequest(
            email="demo@stubichat.com",
            password="DemoPass123!"
        )
        
        try:
            login_tokens, login_user = await auth_service.login_user(login_request)
            print("✅ Login successful!")
            print(f"   Last login: {login_user['last_login_at']}")
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return
        
        # 3. Get current user information
        print("\n3. 👤 Getting current user info...")
        try:
            current_user = await auth_service.get_current_user(login_tokens["access_token"])
            print("✅ Current user retrieved!")
            print(f"   Active: {current_user['is_active']}")
            print(f"   Verified: {current_user['is_verified']}")
        except Exception as e:
            print(f"❌ Failed to get current user: {e}")
            return
        
        # 4. Refresh token
        print("\n4. 🔄 Refreshing access token...")
        try:
            new_tokens = await auth_service.refresh_access_token(login_tokens["refresh_token"])
            print(f"✅ Token refreshed successfully!")
            print(f"   New access token: {new_tokens['access_token'][:50]}...")
        except Exception as e:
            print(f"❌ Token refresh failed: {e}")
            return
        
        # 5. Logout
        print("\n5. 🚪 Logging out...")
        try:
            success = await auth_service.logout_user(user["id"], login_tokens["refresh_token"])
            if success:
                print(f"✅ Logout successful!")
            else:
                print(f"❌ Logout failed!")
        except Exception as e:
            print(f"❌ Logout failed: {e}")
            return
        
        print("\n🎉 Authentication system demo completed successfully!")
        print("=" * 50)


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(demonstrate_auth_system()) 