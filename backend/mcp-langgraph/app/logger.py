"""
Centralized Logging System for MCP RAG Backend

This module provides a comprehensive logging system with the following features:
- Daily log file rotation with configurable naming patterns
- Console output for real-time debugging
- Structured logging with timestamp, level, module, and message
- Exception handling with full tracebacks
- Configurable logging levels
- Extensible design for future log destinations

Usage:
    from app.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("This is an info message")
    logger.error("This is an error message", exc_info=True)
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import traceback
from app.config.base import rag_config


# Global configuration for the logging system
class LoggingConfig:
    """Configuration class for the logging system."""
    
    # Server identification
    SERVER_NAME = "mcpserver"
    
    # Log directory and file settings
    LOG_DIR = "logs"
    LOG_FILE_PREFIX = "logging"
    LOG_FILE_EXTENSION = ".txt"
    
    # Log format settings
    LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s | %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # File rotation settings
    ROTATION_WHEN = "midnight"  # Rotate at midnight
    ROTATION_INTERVAL = 1       # Every 1 day
    BACKUP_COUNT = 30          # Keep 30 days of logs
    
    # Default logging level
    DEFAULT_LEVEL = logging.INFO
    
    # Console output settings
    CONSOLE_OUTPUT = True
    CONSOLE_LEVEL = logging.INFO
    
    # Performance logging settings
    PERFORMANCE_LOGGING = True
    SLOW_OPERATION_THRESHOLD = 1.0  # Log operations taking longer than 1 second


class CustomFormatter(logging.Formatter):
    """
    Custom formatter that adds color coding for console output and
    enhanced formatting for different log levels.
    """
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[41m',   # Red background
    }
    RESET = '\033[0m'
    
    def __init__(self, use_colors: bool = False):
        """
        Initialize the custom formatter.
        
        Args:
            use_colors: Whether to use color coding for console output
        """
        super().__init__()
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with optional color coding.
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted log message
        """
        # Create the base formatter
        formatter = logging.Formatter(
            LoggingConfig.LOG_FORMAT,
            LoggingConfig.DATE_FORMAT
        )
        
        # Get the formatted message
        formatted_message = formatter.format(record)
        
        # Add color coding for console output if enabled
        if self.use_colors and record.levelname in self.COLORS:
            color = self.COLORS[record.levelname]
            formatted_message = f"{color}{formatted_message}{self.RESET}"
        
        return formatted_message


class PerformanceLogger:
    """
    Context manager for logging performance metrics of operations.
    
    Usage:
        with PerformanceLogger(logger, "document_embedding"):
            # Your operation here
            pass
    """
    
    def __init__(self, logger: logging.Logger, operation_name: str, 
                 threshold: float = LoggingConfig.SLOW_OPERATION_THRESHOLD):
        """
        Initialize the performance logger.
        
        Args:
            logger: Logger instance to use
            operation_name: Name of the operation being timed
            threshold: Threshold in seconds to log slow operations
        """
        self.logger = logger
        self.operation_name = operation_name
        self.threshold = threshold
        self.start_time = None
    
    def __enter__(self):
        """Start timing the operation."""
        self.start_time = datetime.now()
        self.logger.debug(f"Starting operation: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log the results."""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            
            if exc_type:
                self.logger.error(
                    f"Operation '{self.operation_name}' failed after {duration:.3f}s",
                    exc_info=True
                )
            elif duration > self.threshold:
                self.logger.warning(
                    f"Slow operation '{self.operation_name}' completed in {duration:.3f}s"
                )
            else:
                self.logger.debug(
                    f"Operation '{self.operation_name}' completed in {duration:.3f}s"
                )


class LoggingManager:
    """
    Manager class for the centralized logging system.
    
    This class handles the setup and configuration of loggers,
    file handlers, and console handlers.
    """
    
    _instance = None
    _initialized = False
    _loggers: Dict[str, logging.Logger] = {}
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(LoggingManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the logging manager."""
        if not self._initialized:
            self._setup_logging_directory()
            self._setup_root_logger()
            LoggingManager._initialized = True
    
    def _setup_logging_directory(self):
        """Create the logging directory if it doesn't exist."""
        log_dir = Path(LoggingConfig.LOG_DIR)
        log_dir.mkdir(exist_ok=True)
        
        # Ensure the directory is writable
        if not os.access(log_dir, os.W_OK):
            raise PermissionError(f"Cannot write to log directory: {log_dir}")
    
    def _setup_root_logger(self):
        """Setup the root logger configuration."""
        root_logger = logging.getLogger()
        root_logger.setLevel(LoggingConfig.DEFAULT_LEVEL)
        
        # Remove any existing handlers to avoid duplicates
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    def _create_file_handler(self) -> logging.Handler:
        """
        Create a rotating file handler for daily log rotation.
        
        Returns:
            Configured file handler
        """
        # Generate log filename with current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        log_filename = (
            f"{LoggingConfig.LOG_FILE_PREFIX}_{LoggingConfig.SERVER_NAME}_{current_date}"
            f"{LoggingConfig.LOG_FILE_EXTENSION}"
        )
        log_filepath = Path(LoggingConfig.LOG_DIR) / log_filename
        
        # Create timed rotating file handler
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=str(log_filepath),
            when=LoggingConfig.ROTATION_WHEN,
            interval=LoggingConfig.ROTATION_INTERVAL,
            backupCount=LoggingConfig.BACKUP_COUNT,
            encoding='utf-8'
        )
        
        # Set formatter for file output (no colors)
        file_formatter = CustomFormatter(use_colors=False)
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(LoggingConfig.DEFAULT_LEVEL)
        
        return file_handler
    
    def _create_console_handler(self) -> logging.Handler:
        """
        Create a console handler for real-time debugging.
        
        Returns:
            Configured console handler
        """
        console_handler = logging.StreamHandler(sys.stdout)
        
        # Set formatter for console output (with colors if supported)
        use_colors = (
            hasattr(sys.stdout, 'isatty') and 
            sys.stdout.isatty() and 
            os.getenv('TERM') != 'dumb'
        )
        console_formatter = CustomFormatter(use_colors=use_colors)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(LoggingConfig.CONSOLE_LEVEL)
        
        return console_handler
    
    def get_logger(self, name: str, level: Optional[int] = None) -> logging.Logger:
        """
        Get or create a logger with the specified name.
        
        Args:
            name: Name of the logger (typically __name__)
            level: Optional logging level override
            
        Returns:
            Configured logger instance
        """
        # Return existing logger if already created
        if name in self._loggers:
            return self._loggers[name]
        
        # Create new logger
        logger = logging.getLogger(name)
        logger.setLevel(level or LoggingConfig.DEFAULT_LEVEL)
        
        # Prevent duplicate logs by not propagating to root logger
        logger.propagate = False
        
        # Add file handler
        file_handler = self._create_file_handler()
        logger.addHandler(file_handler)
        
        # Add console handler if enabled
        if LoggingConfig.CONSOLE_OUTPUT:
            console_handler = self._create_console_handler()
            logger.addHandler(console_handler)
        
        # Store logger reference
        self._loggers[name] = logger
        
        # Log logger creation
        logger.info(f"Logger '{name}' initialized with level {logging.getLevelName(logger.level)}")
        
        return logger
    
    def set_global_level(self, level: int):
        """
        Set the logging level for all existing loggers.
        
        Args:
            level: New logging level
        """
        LoggingConfig.DEFAULT_LEVEL = level
        
        for logger in self._loggers.values():
            logger.setLevel(level)
            for handler in logger.handlers:
                if isinstance(handler, logging.handlers.TimedRotatingFileHandler):
                    handler.setLevel(level)
    
    def add_remote_handler(self, handler: logging.Handler):
        """
        Add a remote logging handler to all existing loggers.
        This method supports extensibility for future log destinations.
        
        Args:
            handler: Remote logging handler (e.g., HTTP, Syslog, Cloud)
        """
        for logger in self._loggers.values():
            logger.addHandler(handler)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the logging system.
        
        Returns:
            Dictionary containing logging statistics
        """
        return {
            "initialized": self._initialized,
            "total_loggers": len(self._loggers),
            "logger_names": list(self._loggers.keys()),
            "log_directory": LoggingConfig.LOG_DIR,
            "server_name": LoggingConfig.SERVER_NAME,
            "current_level": logging.getLevelName(LoggingConfig.DEFAULT_LEVEL),
            "console_output_enabled": LoggingConfig.CONSOLE_OUTPUT,
            "performance_logging_enabled": LoggingConfig.PERFORMANCE_LOGGING
        }


# Global logging manager instance
_logging_manager = LoggingManager()


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get a configured logger instance.
    
    This is the main function to use throughout the codebase.
    
    Args:
        name: Name of the logger (typically __name__)
        level: Optional logging level override
        
    Returns:
        Configured logger instance
        
    Example:
        from app.logger import get_logger
        
        logger = get_logger(__name__)
        logger.info("This is an info message")
        logger.error("This is an error", exc_info=True)
    """
    return _logging_manager.get_logger(name, level)


def set_logging_level(level: int):
    """
    Set the global logging level.
    
    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO)
        
    Example:
        import logging
        from app.logger import set_logging_level
        
        set_logging_level(logging.DEBUG)  # Enable debug logging
    """
    _logging_manager.set_global_level(level)


def add_remote_logging_handler(handler: logging.Handler):
    """
    Add a remote logging handler for extensibility.
    
    Args:
        handler: Remote logging handler
        
    Example:
        import logging.handlers
        from app.logger import add_remote_logging_handler
        
        # Add HTTP handler for remote logging
        http_handler = logging.handlers.HTTPHandler(
            'example.com', '/log', method='POST'
        )
        add_remote_logging_handler(http_handler)
    """
    _logging_manager.add_remote_handler(handler)


def get_performance_logger(logger: logging.Logger, operation_name: str) -> PerformanceLogger:
    """
    Get a performance logger context manager.
    
    Args:
        logger: Logger instance to use
        operation_name: Name of the operation being timed
        
    Returns:
        Performance logger context manager
        
    Example:
        from app.logger import get_logger, get_performance_logger
        
        logger = get_logger(__name__)
        
        with get_performance_logger(logger, "document_embedding"):
            # Your operation here
            result = embed_document(text)
    """
    return PerformanceLogger(logger, operation_name)


def log_exception(logger: logging.Logger, message: str, exc: Optional[Exception] = None):
    """
    Log an exception with full traceback.
    
    Args:
        logger: Logger instance to use
        message: Error message to log
        exc: Optional exception instance
        
    Example:
        from app.logger import get_logger, log_exception
        
        logger = get_logger(__name__)
        
        try:
            # Some operation that might fail
            result = risky_operation()
        except Exception as e:
            log_exception(logger, "Failed to perform risky operation", e)
    """
    if exc:
        logger.error(f"{message}: {str(exc)}", exc_info=True)
    else:
        logger.error(message, exc_info=True)


def get_logging_stats() -> Dict[str, Any]:
    """
    Get comprehensive logging system statistics.
    
    Returns:
        Dictionary containing logging statistics
        
    Example:
        from app.logger import get_logging_stats
        
        stats = get_logging_stats()
        print(f"Total loggers: {stats['total_loggers']}")
    """
    return _logging_manager.get_log_stats()


# Convenience function for backward compatibility
def setup_logging(level: int = logging.INFO):
    """
    Setup logging with specified level.
    
    This function is provided for backward compatibility and convenience.
    The logging system is automatically initialized when importing this module.
    
    Args:
        level: Logging level to set
    """
    set_logging_level(level)


# Initialize logging on module import
logger = get_logger(__name__)
logger.info(f"Centralized logging system initialized for server: {LoggingConfig.SERVER_NAME}")
logger.info(f"Log files will be stored in: {Path(LoggingConfig.LOG_DIR).absolute()}")
logger.info(f"Log rotation: daily at midnight, keeping {LoggingConfig.BACKUP_COUNT} days of logs")

# Export main functions and classes
__all__ = [
    'get_logger',
    'set_logging_level', 
    'add_remote_logging_handler',
    'get_performance_logger',
    'log_exception',
    'get_logging_stats',
    'setup_logging',
    'LoggingConfig',
    'PerformanceLogger'
] 