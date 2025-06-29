"""
Centralized Logging System for VLLM Server

This module provides a comprehensive logging system with the following features:
- Daily log file rotation with configurable naming patterns
- Console output for real-time debugging
- Structured logging with timestamp, level, module, and message
- Request ID tracking for distributed tracing
- Model inference performance monitoring
- Exception handling with full tracebacks
- Configurable logging levels
- Extensible design for future log destinations

Usage:
    from app.logger import get_logger, get_request_logger
    
    logger = get_logger(__name__)
    logger.info("Model inference started")
    
    # For request tracking
    request_logger = get_request_logger("req_123")
    request_logger.info("Processing generate request")
"""

import logging
import logging.handlers
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from contextvars import ContextVar
import traceback
import json
from app.config.base import settings

# Context variable for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')


# Global configuration for the logging system
class LoggingConfig:
    """Configuration class for the VLLM server logging system."""
    
    # Server identification
    SERVER_NAME = "vllmserver"
    
    # Log directory and file settings
    LOG_DIR = "logs"
    LOG_FILE_PREFIX = "logging"
    LOG_FILE_EXTENSION = ".txt"
    
    # Log format settings
    LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(funcName)-20s | %(request_id)s | %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # File rotation settings
    ROTATION_WHEN = "midnight"  # Rotate at midnight
    ROTATION_INTERVAL = 1       # Every 1 day
    BACKUP_COUNT = 30          # Keep 30 days of logs
    
    # Default logging level (configurable via environment)
    DEFAULT_LEVEL = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO)
    
    # Console output settings
    CONSOLE_OUTPUT = True
    CONSOLE_LEVEL = getattr(logging, os.getenv('CONSOLE_LOG_LEVEL', 'INFO').upper(), logging.INFO)
    
    # Performance logging settings
    PERFORMANCE_LOGGING = True
    SLOW_OPERATION_THRESHOLD = float(os.getenv('SLOW_OPERATION_THRESHOLD', '2.0'))  # VLLM inference can be slower
    
    # Request tracking settings
    REQUEST_TRACKING = True
    LOG_REQUEST_BODY = os.getenv('LOG_REQUEST_BODY', 'true').lower() == 'true'
    MAX_BODY_SIZE_LOG = int(os.getenv('MAX_BODY_SIZE_LOG', '1000'))  # Max chars to log from request body


class RequestAwareFormatter(logging.Formatter):
    """
    Custom formatter that includes request ID and adds color coding for console output.
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
        Format the log record with request ID and optional color coding.
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted log message
        """
        # Add request ID to the record
        record.request_id = request_id_var.get() or 'no-req'
        
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


class ModelPerformanceLogger:
    """
    Context manager for logging model inference performance metrics.
    
    Usage:
        with ModelPerformanceLogger(logger, "text_generation", prompt_tokens=100):
            result = model.generate(prompt)
            # Automatically logs inference time and token throughput
    """
    
    def __init__(self, logger: logging.Logger, operation_name: str, 
                 prompt_tokens: Optional[int] = None,
                 threshold: float = LoggingConfig.SLOW_OPERATION_THRESHOLD):
        """
        Initialize the model performance logger.
        
        Args:
            logger: Logger instance to use
            operation_name: Name of the operation being timed
            prompt_tokens: Number of tokens in the prompt (for throughput calculation)
            threshold: Threshold in seconds to log slow operations
        """
        self.logger = logger
        self.operation_name = operation_name
        self.prompt_tokens = prompt_tokens
        self.threshold = threshold
        self.start_time = None
        self.completion_tokens = 0
    
    def __enter__(self):
        """Start timing the operation."""
        self.start_time = datetime.now()
        req_id = request_id_var.get() or 'no-req'
        self.logger.debug(f"Starting {self.operation_name} (req: {req_id}, prompt_tokens: {self.prompt_tokens})")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log the results."""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            req_id = request_id_var.get() or 'no-req'
            
            if exc_type:
                self.logger.error(
                    f"Operation '{self.operation_name}' failed after {duration:.3f}s (req: {req_id})",
                    exc_info=True
                )
            else:
                # Calculate throughput metrics
                metrics = {
                    "duration": duration,
                    "operation": self.operation_name,
                    "request_id": req_id
                }
                
                if self.prompt_tokens:
                    metrics["prompt_tokens"] = self.prompt_tokens
                    metrics["tokens_per_second"] = self.prompt_tokens / duration if duration > 0 else 0
                
                if self.completion_tokens > 0:
                    metrics["completion_tokens"] = self.completion_tokens
                    metrics["total_tokens"] = self.prompt_tokens + self.completion_tokens
                    metrics["completion_tokens_per_second"] = self.completion_tokens / duration if duration > 0 else 0
                
                if duration > self.threshold:
                    self.logger.warning(
                        f"Slow {self.operation_name}: {duration:.3f}s "
                        f"(tokens/s: {metrics.get('tokens_per_second', 'N/A'):.1f}) - {metrics}"
                    )
                else:
                    self.logger.info(
                        f"{self.operation_name} completed: {duration:.3f}s "
                        f"(tokens/s: {metrics.get('tokens_per_second', 'N/A'):.1f})"
                    )
    
    def set_completion_tokens(self, count: int):
        """Set the number of completion tokens for throughput calculation."""
        self.completion_tokens = count


class VLLMLoggingManager:
    """
    Manager class for the VLLM server centralized logging system.
    
    This class handles the setup and configuration of loggers,
    file handlers, console handlers, and request tracking.
    """
    
    _instance = None
    _initialized = False
    _loggers: Dict[str, logging.Logger] = {}
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(VLLMLoggingManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the logging manager."""
        if not self._initialized:
            self._setup_logging_directory()
            self._setup_root_logger()
            VLLMLoggingManager._initialized = True
    
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
        file_formatter = RequestAwareFormatter(use_colors=False)
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
        console_formatter = RequestAwareFormatter(use_colors=use_colors)
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
            "performance_logging_enabled": LoggingConfig.PERFORMANCE_LOGGING,
            "request_tracking_enabled": LoggingConfig.REQUEST_TRACKING
        }


# Global logging manager instance
_logging_manager = VLLMLoggingManager()


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get a configured logger instance.
    
    This is the main function to use throughout the VLLM server codebase.
    
    Args:
        name: Name of the logger (typically __name__)
        level: Optional logging level override
        
    Returns:
        Configured logger instance
        
    Example:
        from app.logger import get_logger
        
        logger = get_logger(__name__)
        logger.info("Model inference started")
        logger.error("Model loading failed", exc_info=True)
    """
    return _logging_manager.get_logger(name, level)


def get_request_logger(request_id: str = None) -> logging.Logger:
    """
    Get a logger configured for request tracking.
    
    Args:
        request_id: Optional request ID (will generate one if not provided)
        
    Returns:
        Logger instance with request context
        
    Example:
        from app.logger import get_request_logger
        
        request_logger = get_request_logger("req_123")
        request_logger.info("Processing generation request")
    """
    if not request_id:
        request_id = f"req_{uuid.uuid4().hex[:8]}"
    
    # Set the request ID in context
    request_id_var.set(request_id)
    
    return get_logger("request")


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
            'logs.example.com', '/vllm-logs', method='POST'
        )
        add_remote_logging_handler(http_handler)
    """
    _logging_manager.add_remote_handler(handler)


def get_model_performance_logger(logger: logging.Logger, operation_name: str, 
                                prompt_tokens: Optional[int] = None) -> ModelPerformanceLogger:
    """
    Get a model performance logger context manager.
    
    Args:
        logger: Logger instance to use
        operation_name: Name of the operation being timed
        prompt_tokens: Number of tokens in the prompt
        
    Returns:
        Model performance logger context manager
        
    Example:
        from app.logger import get_logger, get_model_performance_logger
        
        logger = get_logger(__name__)
        
        with get_model_performance_logger(logger, "text_generation", prompt_tokens=150) as perf_logger:
            result = model.generate(prompt)
            perf_logger.set_completion_tokens(len(result.split()))
    """
    return ModelPerformanceLogger(logger, operation_name, prompt_tokens)


def log_exception(logger: logging.Logger, message: str, exc: Optional[Exception] = None):
    """
    Log an exception with full traceback and request context.
    
    Args:
        logger: Logger instance to use
        message: Error message to log
        exc: Optional exception instance
        
    Example:
        from app.logger import get_logger, log_exception
        
        logger = get_logger(__name__)
        
        try:
            result = model.generate(prompt)
        except Exception as e:
            log_exception(logger, "Model inference failed", e)
    """
    req_id = request_id_var.get() or 'no-req'
    if exc:
        logger.error(f"{message} (req: {req_id}): {str(exc)}", exc_info=True)
    else:
        logger.error(f"{message} (req: {req_id})", exc_info=True)


def log_request_info(logger: logging.Logger, method: str, endpoint: str, 
                    client_ip: str = None, body_size: int = None, 
                    body_preview: str = None):
    """
    Log incoming API request information.
    
    Args:
        logger: Logger instance to use
        method: HTTP method
        endpoint: API endpoint
        client_ip: Client IP address
        body_size: Size of request body in bytes
        body_preview: Preview of request body (truncated)
        
    Example:
        from app.logger import get_request_logger, log_request_info
        
        request_logger = get_request_logger()
        log_request_info(request_logger, "POST", "/generate", "192.168.1.1", 150, "prompt: Hello...")
    """
    req_id = request_id_var.get() or 'no-req'
    
    info_parts = [f"{method} {endpoint}"]
    if client_ip:
        info_parts.append(f"client_ip={client_ip}")
    if body_size is not None:
        info_parts.append(f"body_size={body_size}B")
    
    message = f"Request received: {' | '.join(info_parts)}"
    
    if body_preview and LoggingConfig.LOG_REQUEST_BODY:
        if len(body_preview) > LoggingConfig.MAX_BODY_SIZE_LOG:
            body_preview = body_preview[:LoggingConfig.MAX_BODY_SIZE_LOG] + "..."
        message += f" | body_preview: {body_preview}"
    
    logger.info(message)


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
logger.info(f"VLLM Server centralized logging system initialized")
logger.info(f"Server: {LoggingConfig.SERVER_NAME} | Log level: {logging.getLevelName(LoggingConfig.DEFAULT_LEVEL)}")
logger.info(f"Log files will be stored in: {Path(LoggingConfig.LOG_DIR).absolute()}")
logger.info(f"Log rotation: daily at midnight, keeping {LoggingConfig.BACKUP_COUNT} days of logs")
logger.info(f"Request tracking: {LoggingConfig.REQUEST_TRACKING} | Performance monitoring: {LoggingConfig.PERFORMANCE_LOGGING}")

# Export main functions and classes
__all__ = [
    'get_logger',
    'get_request_logger',
    'set_logging_level', 
    'add_remote_logging_handler',
    'get_model_performance_logger',
    'log_exception',
    'log_request_info',
    'get_logging_stats',
    'setup_logging',
    'LoggingConfig',
    'ModelPerformanceLogger'
] 