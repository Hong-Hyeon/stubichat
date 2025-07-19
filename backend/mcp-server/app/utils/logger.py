import logging
import sys
from typing import Optional
from app.core.config import get_settings


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Get a configured logger instance."""
    settings = get_settings()
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Set log level
    log_level = level or settings.log_level
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger


def log_request_info(logger: logging.Logger, method: str, path: str, status_code: int, duration: float):
    """Log request information."""
    logger.info(f"Response: {method} {path} - {status_code} ({duration:.3f}s)") 