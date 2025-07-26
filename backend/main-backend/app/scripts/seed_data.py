#!/usr/bin/env python3
"""
Seed script for creating test data.
Run this script to populate the database with test users.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.core.database import AsyncSessionLocal, init_db
from app.factory.auth_service_factory import get_auth_service_factory
from app.schemas.auth import UserRegisterRequest


async def create_test_users():
    """Create test users for development."""
    
    # Initialize database
    await init_db()
    
    # Test users data
    test_users = [
        {
            "email": "admin@stubichat.com",
            "password": "Admin123!",
            "name": "Admin User"
        },
        {
            "email": "user@stubichat.com",
            "password": "User123!",
            "name": "Test User"
        },
        {
            "email": "demo@stubichat.com",
            "password": "Demo123!",
            "name": "Demo User"
        }
    ]
    
    async with AsyncSessionLocal() as session:
        auth_service_factory = get_auth_service_factory()
        auth_service = auth_service_factory.create_auth_service(session)
        
        created_users = []
        
        for user_data in test_users:
            try:
                request = UserRegisterRequest(**user_data)
                tokens, user = await auth_service.register_user(request)
                created_users.append({
                    "email": user_data["email"],
                    "name": user_data["name"],
                    "access_token": tokens["access_token"]
                })
                print(f"✅ Created user: {user_data['email']}")
                
            except Exception as e:
                print(f"❌ Failed to create user {user_data['email']}: {str(e)}")
        
        print(f"\n🎉 Successfully created {len(created_users)} test users!")
        print("\nTest users created:")
        for user in created_users:
            print(f"  - {user['email']} ({user['name']})")
        
        if created_users:
            print(f"\n🔑 Sample access token for {created_users[0]['email']}:")
            print(f"   {created_users[0]['access_token']}")


async def main():
    """Main function."""
    print("🌱 Starting database seeding...")
    
    try:
        await create_test_users()
        print("\n✅ Database seeding completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Database seeding failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 