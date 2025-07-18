from pydantic_settings import BaseSettings
from typing import Optional
import os
from pydantic import Field


class Settings(BaseSettings):
    # Application settings
    app_name: str = "Stubichat LLM Agent"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8001
    
    # OpenAI settings
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_base_url: Optional[str] = Field(default=None, description="OpenAI base URL (for custom endpoints)")
    openai_organization: Optional[str] = Field(default=None, description="OpenAI organization ID")
    
    # Model settings
    default_model: str = "gpt-4"
    max_tokens: int = 4000
    temperature: float = 0.7
    
    # Rate limiting
    rate_limit_per_minute: int = 60
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    
    # CORS settings
    cors_origins: list = ["http://localhost:3000", "http://localhost:8000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings 