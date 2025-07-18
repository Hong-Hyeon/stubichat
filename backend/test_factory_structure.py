#!/usr/bin/env python3
"""
Test script to verify factory pattern structure and .env file loading.
This test doesn't require dependencies to be installed.
"""

import os
import sys
from pathlib import Path


def test_file_structure():
    """Test that all factory pattern files exist."""
    print("🧪 Testing Factory Pattern File Structure")
    print("=" * 50)
    
    backend_dir = Path(__file__).parent
    required_files = [
        "main-backend/app/factory/app_factory.py",
        "main-backend/app/factory/service_factory.py",
        "llm-agent/app/factory/app_factory.py",
        "llm-agent/app/factory/service_factory.py",
        "main-backend/app/core/config.py",
        "llm-agent/app/core/config.py",
        "main-backend/app/main.py",
        "llm-agent/app/main.py",
        "env.example"
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = backend_dir / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            all_exist = False
    
    return all_exist


def test_env_file():
    """Test .env file configuration."""
    print("\n🧪 Testing Environment Configuration")
    print("=" * 40)
    
    backend_dir = Path(__file__).parent
    env_file = backend_dir / ".env"
    example_file = backend_dir / "env.example"
    
    # Check if .env exists
    if env_file.exists():
        print("✅ .env file exists")
        
        # Check for OpenAI API key
        with open(env_file, 'r') as f:
            content = f.read()
            if "OPENAI_API_KEY=your-openai-api-key-here" in content:
                print("⚠️  OpenAI API key not configured (using placeholder)")
            elif "OPENAI_API_KEY=" in content:
                print("✅ OpenAI API key is configured")
            else:
                print("❌ OpenAI API key configuration not found")
    else:
        print("⚠️  .env file not found")
        
        # Check if example exists
        if example_file.exists():
            print("✅ env.example exists - you can copy it to .env")
        else:
            print("❌ env.example not found")
    
    return True


def test_factory_pattern_content():
    """Test that factory pattern files contain expected content."""
    print("\n🧪 Testing Factory Pattern Content")
    print("=" * 40)
    
    backend_dir = Path(__file__).parent
    
    # Test main backend app factory
    main_app_factory = backend_dir / "main-backend/app/factory/app_factory.py"
    if main_app_factory.exists():
        with open(main_app_factory, 'r') as f:
            content = f.read()
            if "class AppFactory:" in content:
                print("✅ Main Backend AppFactory class found")
            else:
                print("❌ Main Backend AppFactory class not found")
                return False
            
            if "def create_app(" in content:
                print("✅ Main Backend create_app function found")
            else:
                print("❌ Main Backend create_app function not found")
                return False
    
    # Test LLM agent app factory
    llm_app_factory = backend_dir / "llm-agent/app/factory/app_factory.py"
    if llm_app_factory.exists():
        with open(llm_app_factory, 'r') as f:
            content = f.read()
            if "class AppFactory:" in content:
                print("✅ LLM Agent AppFactory class found")
            else:
                print("❌ LLM Agent AppFactory class not found")
                return False
            
            if "def create_app(" in content:
                print("✅ LLM Agent create_app function found")
            else:
                print("❌ LLM Agent create_app function not found")
                return False
    
    # Test service factories
    main_service_factory = backend_dir / "main-backend/app/factory/service_factory.py"
    llm_service_factory = backend_dir / "llm-agent/app/factory/service_factory.py"
    
    if main_service_factory.exists():
        with open(main_service_factory, 'r') as f:
            content = f.read()
            if "class ServiceFactory:" in content:
                print("✅ Main Backend ServiceFactory class found")
            else:
                print("❌ Main Backend ServiceFactory class not found")
                return False
    
    if llm_service_factory.exists():
        with open(llm_service_factory, 'r') as f:
            content = f.read()
            if "class ServiceFactory:" in content:
                print("✅ LLM Agent ServiceFactory class found")
            else:
                print("❌ LLM Agent ServiceFactory class not found")
                return False
    
    return True


def test_config_content():
    """Test that config files contain expected content."""
    print("\n🧪 Testing Configuration Content")
    print("=" * 35)
    
    backend_dir = Path(__file__).parent
    
    # Test main backend config
    main_config = backend_dir / "main-backend/app/core/config.py"
    if main_config.exists():
        with open(main_config, 'r') as f:
            content = f.read()
            if "class Settings(BaseSettings):" in content:
                print("✅ Main Backend Settings class found")
            else:
                print("❌ Main Backend Settings class not found")
                return False
            
            if "def get_settings()" in content:
                print("✅ Main Backend get_settings function found")
            else:
                print("❌ Main Backend get_settings function not found")
                return False
            
            if "load_dotenv" in content:
                print("✅ Main Backend dotenv loading found")
            else:
                print("❌ Main Backend dotenv loading not found")
                return False
    
    # Test LLM agent config
    llm_config = backend_dir / "llm-agent/app/core/config.py"
    if llm_config.exists():
        with open(llm_config, 'r') as f:
            content = f.read()
            if "class Settings(BaseSettings):" in content:
                print("✅ LLM Agent Settings class found")
            else:
                print("❌ LLM Agent Settings class not found")
                return False
            
            if "def get_settings()" in content:
                print("✅ LLM Agent get_settings function found")
            else:
                print("❌ LLM Agent get_settings function not found")
                return False
            
            if "load_dotenv" in content:
                print("✅ LLM Agent dotenv loading found")
            else:
                print("❌ LLM Agent dotenv loading not found")
                return False
    
    return True


def test_main_files():
    """Test that main.py files use the factory pattern."""
    print("\n🧪 Testing Main Files")
    print("=" * 25)
    
    backend_dir = Path(__file__).parent
    
    # Test main backend main.py
    main_py = backend_dir / "main-backend/app/main.py"
    if main_py.exists():
        with open(main_py, 'r') as f:
            content = f.read()
            if "from app.factory.app_factory import create_app" in content:
                print("✅ Main Backend uses factory pattern")
            else:
                print("❌ Main Backend doesn't use factory pattern")
                return False
    
    # Test LLM agent main.py
    llm_py = backend_dir / "llm-agent/app/main.py"
    if llm_py.exists():
        with open(llm_py, 'r') as f:
            content = f.read()
            if "from app.factory.app_factory import create_app" in content:
                print("✅ LLM Agent uses factory pattern")
            else:
                print("❌ LLM Agent doesn't use factory pattern")
                return False
    
    return True


def main():
    """Run all tests."""
    print("🚀 Stubichat Factory Pattern Structure Test")
    print("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Environment Configuration", test_env_file),
        ("Factory Pattern Content", test_factory_pattern_content),
        ("Configuration Content", test_config_content),
        ("Main Files", test_main_files)
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        try:
            result = test_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ {test_name} failed with error: {str(e)}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All Factory Pattern Structure Tests Passed!")
        print("\nNext Steps:")
        print("1. Copy env.example to .env and configure your OpenAI API key")
        print("2. Install dependencies: pip install -r main-backend/requirements.txt")
        print("3. Install dependencies: pip install -r llm-agent/requirements.txt")
        print("4. Run 'docker-compose up' to start the services")
        print("5. Test the endpoints with the provided test scripts")
        sys.exit(0)
    else:
        print("❌ Some Factory Pattern Structure Tests Failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 