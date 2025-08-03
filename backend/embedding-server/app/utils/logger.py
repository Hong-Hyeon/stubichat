import logging
import sys
from typing import Optional


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Get a logger instance with proper configuration."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(getattr(logging, level or "INFO"))
        
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level or "INFO"))
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
    
    return logger 