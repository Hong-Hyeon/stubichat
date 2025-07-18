import sys
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any
from loguru import logger
from app.core.config import settings


def setup_logger():
    """Setup application logger with proper configuration."""
    # Remove default logger
    logger.remove()
    
    # Add console logger
    logger.add(
        sys.stdout,
        format=settings.log_format,
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Add file logger for production
    if not settings.debug:
        logger.add(
            "logs/llm-agent.log",
            format=settings.log_format,
            level=settings.log_level,
            rotation="10 MB",
            retention="7 days",
            compression="gz"
        )
    
    return logger


def get_logger(name: str):
    """Get a logger instance for a specific module."""
    return logger.bind(module=name)


@contextmanager
def log_performance(logger_instance, operation: str):
    """Context manager for logging operation performance."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger_instance.info(f"{operation} completed in {duration:.3f}s")


def log_request_info(logger_instance, method: str, path: str, status_code: int, duration: float):
    """Log HTTP request information."""
    logger_instance.info(
        f"Request: {method} {path} - Status: {status_code} - Duration: {duration:.3f}s"
    )


def log_exception(logger_instance, message: str, exception: Exception):
    """Log exception with proper formatting."""
    logger_instance.exception(f"{message}: {str(exception)}")


# Initialize logger
setup_logger() 