from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    app_name: str = "Stubichat MCP Server"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8002
    
    # CORS settings
    cors_origins: List[str] = ["*"]
    
    # MCP settings
    mcp_server_name: str = "stubichat-mcp"
    mcp_server_version: str = "1.0.0"
    mcp_server_description: str = "MCP server for Stubichat with echo tool"
    
    # Embedding server settings
    embedding_server_url: str = "http://embedding-server:8003"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings 