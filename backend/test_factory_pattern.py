#!/usr/bin/env python3
"""
Test script to verify factory pattern implementation and .env file loading.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import with correct directory names
import sys
sys.path.insert(0, str(backend_dir / "main-backend"))
sys.path.insert(0, str(backend_dir / "llm-agent"))

from app.factory.app_factory import create_app as create_main_app
from app.factory.app_factory import create_app as create_llm_app
from app.factory.service_factory import get_service_factory as get_main_service_factory
from app.factory.service_factory import get_service_factory as get_llm_service_factory
from app.core.config import get_settings as get_main_settings
from app.core.config import get_settings as get_llm_settings


async def test_factory_pattern():
    """Test the factory pattern implementation."""
    print("🧪 Testing Factory Pattern Implementation")
    print("=" * 50)
    
    # Test 1: Configuration loading
    print("\n1. Testing Configuration Loading...")
    try:
        main_settings = get_main_settings()
        llm_settings = get_llm_settings()
        
        print("✅ Main Backend Settings:")
        print(f"   - App Name: {main_settings.app_name}")
        print(f"   - Version: {main_settings.app_version}")
        print(f"   - Debug: {main_settings.debug}")
        print(f"   - LLM Agent URL: {main_settings.llm_agent_url}")
        
        print("✅ LLM Agent Settings:")
        print(f"   - App Name: {llm_settings.app_name}")
        print(f"   - Version: {llm_settings.app_version}")
        print(f"   - Debug: {llm_settings.debug}")
        print(f"   - Default Model: {llm_settings.default_model}")
        
        # Check if OpenAI API key is loaded
        if llm_settings.openai_api_key and llm_settings.openai_api_key != "your-openai-api-key-here":
            print(f"   - OpenAI API Key: {'*' * 10}...{llm_settings.openai_api_key[-4:]}")
        else:
            print(f"   - OpenAI API Key: Not configured (using placeholder)")
            
    except Exception as e:
        print(f"❌ Configuration loading failed: {str(e)}")
        return False
    
    # Test 2: Service Factory
    print("\n2. Testing Service Factory...")
    try:
        main_service_factory = get_main_service_factory()
        llm_service_factory = get_llm_service_factory()
        
        print("✅ Main Backend Service Factory created")
        print(f"   - LLM Client: {type(main_service_factory.llm_client).__name__}")
        print(f"   - Conversation Graph: {type(main_service_factory.conversation_graph).__name__}")
        
        print("✅ LLM Agent Service Factory created")
        print(f"   - OpenAI Service: {type(llm_service_factory.openai_service).__name__}")
        
    except Exception as e:
        print(f"❌ Service factory creation failed: {str(e)}")
        return False
    
    # Test 3: App Factory
    print("\n3. Testing App Factory...")
    try:
        main_app = create_main_app()
        llm_app = create_llm_app()
        
        print("✅ Main Backend App created")
        print(f"   - Title: {main_app.title}")
        print(f"   - Version: {main_app.version}")
        print(f"   - Routes: {len(main_app.routes)}")
        
        print("✅ LLM Agent App created")
        print(f"   - Title: {llm_app.title}")
        print(f"   - Version: {llm_app.version}")
        print(f"   - Routes: {len(llm_app.routes)}")
        
    except Exception as e:
        print(f"❌ App factory creation failed: {str(e)}")
        return False
    
    # Test 4: Environment Variables
    print("\n4. Testing Environment Variables...")
    try:
        # Check if .env file exists
        env_file = backend_dir / ".env"
        if env_file.exists():
            print(f"✅ .env file found at: {env_file}")
            
            # Check key environment variables
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key and openai_key != "your-openai-api-key-here":
                print(f"✅ OPENAI_API_KEY is configured")
            else:
                print(f"⚠️  OPENAI_API_KEY not configured (using placeholder)")
                
            debug_mode = os.getenv("DEBUG", "false").lower()
            print(f"✅ DEBUG mode: {debug_mode}")
            
        else:
            print(f"⚠️  .env file not found at: {env_file}")
            print(f"   Creating from example...")
            
            # Copy from example if .env doesn't exist
            example_file = backend_dir / "env.example"
            if example_file.exists():
                import shutil
                shutil.copy(example_file, env_file)
                print(f"✅ Created .env from env.example")
            else:
                print(f"❌ env.example not found")
                
    except Exception as e:
        print(f"❌ Environment variable test failed: {str(e)}")
        return False
    
    # Test 5: Service Health (if services are running)
    print("\n5. Testing Service Health...")
    try:
        import httpx
        
        # Test main backend health
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:8000/health")
                if response.status_code == 200:
                    print(f"✅ Main Backend is running")
                else:
                    print(f"⚠️  Main Backend health check failed: {response.status_code}")
        except Exception:
            print(f"⚠️  Main Backend not running (expected if not started)")
        
        # Test LLM agent health
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:8001/health")
                if response.status_code == 200:
                    print(f"✅ LLM Agent is running")
                else:
                    print(f"⚠️  LLM Agent health check failed: {response.status_code}")
        except Exception:
            print(f"⚠️  LLM Agent not running (expected if not started)")
            
    except Exception as e:
        print(f"❌ Service health test failed: {str(e)}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Factory Pattern Test Completed Successfully!")
    print("\nNext Steps:")
    print("1. Copy env.example to .env and configure your OpenAI API key")
    print("2. Run 'docker-compose up' to start the services")
    print("3. Test the endpoints with the provided test scripts")
    
    return True


async def test_dependency_injection():
    """Test dependency injection with FastAPI."""
    print("\n🧪 Testing Dependency Injection")
    print("=" * 30)
    
    try:
        from app.api.chat import get_llm_client
        from app.api.generate import get_openai_service
        
        # Test dependency functions
        main_service_factory = get_main_service_factory()
        llm_service_factory = get_llm_service_factory()
        
        llm_client = get_llm_client(main_service_factory)
        openai_service = get_openai_service(llm_service_factory)
        
        print(f"✅ LLM Client dependency: {type(llm_client).__name__}")
        print(f"✅ OpenAI Service dependency: {type(openai_service).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Dependency injection test failed: {str(e)}")
        return False


if __name__ == "__main__":
    async def main():
        print("🚀 Stubichat Factory Pattern Test Suite")
        print("=" * 60)
        
        # Run tests
        factory_success = await test_factory_pattern()
        injection_success = await test_dependency_injection()
        
        if factory_success and injection_success:
            print("\n✅ All tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    
    asyncio.run(main()) 