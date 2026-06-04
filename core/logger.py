"""
Centralized logging configuration for API errors and model failures.

Provides structured logging to detect production issues with proper severity levels,
context information, and stack traces for debugging.
"""

import logging
import sys
from datetime import datetime
from functools import wraps
from typing import Any, Callable

# Configure logging format with timestamp, level, and context
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Initialize logger with standardized format and handlers.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Console handler for all logs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def log_errors(logger: logging.Logger) -> Callable:
    """
    Decorator to automatically log errors and exceptions in functions.

    Usage:
        @log_errors(logger)
        def my_function():
            pass

    Args:
        logger: Logger instance to use

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                logger.debug(f"Executing {func.__name__} with args={args}, kwargs={kwargs}")
                result = func(*args, **kwargs)
                logger.debug(f"{func.__name__} completed successfully")
                return result
            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    exc_info=True,
                    extra={
                        "function": func.__name__,
                        "args": str(args)[:100],
                        "kwargs": str(kwargs)[:100],
                    }
                )
                raise
        return wrapper
    return decorator


class APILogger:
    """Specialized logger for API request/response tracking."""

    def __init__(self, name: str = "API"):
        self.logger = setup_logger(name)

    def log_request(self, endpoint: str, method: str, **kwargs: Any) -> None:
        """Log incoming API request."""
        self.logger.info(f"API Request: {method} {endpoint}", extra=kwargs)

    def log_response(self, endpoint: str, status_code: int, duration_ms: float) -> None:
        """Log API response with timing."""
        self.logger.info(f"API Response: {endpoint} - Status {status_code} ({duration_ms}ms)")

    def log_error(self, endpoint: str, error: Exception, status_code: int = 500) -> None:
        """Log API error with full context."""
        self.logger.error(
            f"API Error: {endpoint} - Status {status_code}",
            exc_info=True,
            extra={"error_type": type(error).__name__}
        )


class ModelLogger:
    """Specialized logger for model operations."""

    def __init__(self, name: str = "Model"):
        self.logger = setup_logger(name)

    def log_load_start(self, model_name: str) -> None:
        """Log model loading start."""
        self.logger.info(f"Loading model: {model_name}")

    def log_load_success(self, model_name: str, duration_ms: float) -> None:
        """Log successful model load."""
        self.logger.info(f"Model loaded successfully: {model_name} ({duration_ms}ms)")

    def log_load_failure(self, model_name: str, error: Exception) -> None:
        """Log model loading failure."""
        self.logger.error(
            f"Failed to load model: {model_name}",
            exc_info=True,
            extra={"error_type": type(error).__name__}
        )

    def log_inference_start(self, model_name: str, operation: str) -> None:
        """Log model inference start."""
        self.logger.debug(f"Model inference: {model_name} - {operation}")

    def log_inference_error(self, model_name: str, operation: str, error: Exception) -> None:
        """Log model inference error."""
        self.logger.error(
            f"Model inference failed: {model_name} - {operation}",
            exc_info=True,
            extra={"error_type": type(error).__name__}
        )


# Global logger instances
api_logger = APILogger()
model_logger = ModelLogger()
app_logger = setup_logger("app")
