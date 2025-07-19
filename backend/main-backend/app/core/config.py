from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    app_name: str = "Stubichat Main Backend"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # LLM Agent service settings
    llm_agent_url: str = "http://localhost:8001"
    llm_agent_timeout: int = 30
    
    # MCP Server settings
    mcp_server_url: str = "http://mcp-server:8002"
    
    # OpenAI settings (for direct fallback)
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    
    # Database settings (optional)
    database_url: Optional[str] = None
    
    # Security settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    
    # CORS settings - Updated for frontend integration
    cors_origins: List[str] = [
        "http://localhost:3000", 
        "http://localhost:3001",
        "http://frontend:3000",  # Docker container name
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


def get_settings() -> Settings:
    """Get application settings with proper .env loading."""
    # Load .env file from the project root
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
    
    return Settings()


# Global settings instance
settings = get_settings() 