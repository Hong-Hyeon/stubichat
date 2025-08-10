import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8003
    debug: bool = True
    log_level: str = "INFO"
    
    # Database settings
    embedding_database_url: str = "postgresql://embedding_user:embedding_password@embedding_postgres:5432/embeddings"
    
    # Redis settings
    redis_url: str = "redis://redis:6379/1"
    
    # OpenAI settings
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "text-embedding-ada-002"
    
    # Celery settings
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/1"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create settings instance
settings = Settings() 