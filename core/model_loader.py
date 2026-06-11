"""
Model loading with comprehensive error handling and recovery mechanisms.

Provides robust model loading with graceful fallbacks, detailed error logging,
and recovery strategies for missing models, configuration errors, and runtime failures.
"""

import logging
import os
from typing import Optional, Any
from functools import wraps
import traceback


logger = logging.getLogger(__name__)


class ModelLoadError(Exception):
    """Raised when model loading fails."""
    pass


class ModelNotFoundError(ModelLoadError):
    """Raised when model file is not found."""
    pass


class ConfigurationError(ModelLoadError):
    """Raised when model configuration is invalid."""
    pass


def with_model_error_handling(fallback=None):
    """
    Decorator for model loading functions to provide consistent error handling.

    Args:
        fallback: Optional fallback value if loading fails

    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                logger.info(f"Attempting to load model via {func.__name__}")
                result = func(*args, **kwargs)
                logger.info(f"Successfully loaded model via {func.__name__}")
                return result
            except FileNotFoundError as e:
                logger.error(f"Model file not found: {str(e)}")
                logger.debug(traceback.format_exc())
                if fallback is not None:
                    logger.warning(f"Using fallback for {func.__name__}")
                    return fallback
                raise ModelNotFoundError(f"Model file not found: {str(e)}")
            except Exception as e:
                logger.error(f"Model loading failed in {func.__name__}: {str(e)}")
                logger.debug(traceback.format_exc())
                if fallback is not None:
                    logger.warning(f"Using fallback for {func.__name__}")
                    return fallback
                raise ModelLoadError(f"Failed to load model: {str(e)}")
        return wrapper
    return decorator


class ModelLoader:
    """Manages safe model loading with recovery and fallback strategies."""

    def __init__(self, config: dict):
        self.config = config
        self.loaded_models = {}
        self.model_errors = {}

    def validate_model_path(self, model_path: str) -> bool:
        """
        Validate that model path exists and is readable.

        Args:
            model_path: Path to model file

        Returns:
            True if valid, False otherwise
        """
        if not model_path:
            logger.error("Model path is empty")
            return False

        if not os.path.exists(model_path):
            logger.error(f"Model path does not exist: {model_path}")
            return False

        if not os.path.isfile(model_path):
            logger.error(f"Model path is not a file: {model_path}")
            return False

        if not os.access(model_path, os.R_OK):
            logger.error(f"Model file is not readable: {model_path}")
            return False

        try:
            file_size_mb = os.path.getsize(model_path) / (1024 * 1024)
            logger.info(f"Model file found: {model_path} ({file_size_mb:.1f} MB)")
            return True
        except OSError as e:
            logger.error(f"Failed to access model file: {str(e)}")
            return False

    def validate_config(self, model_config: dict, required_keys: list = None) -> bool:
        """
        Validate model configuration.

        Args:
            model_config: Model configuration dictionary
            required_keys: List of required config keys

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(model_config, dict):
            logger.error("Model configuration must be a dictionary")
            return False

        if required_keys:
            missing_keys = [key for key in required_keys if key not in model_config]
            if missing_keys:
                logger.error(f"Missing required config keys: {missing_keys}")
                return False

        return True

    def get_model_status(self, model_name: str) -> dict:
        """
        Get status of a specific model.

        Args:
            model_name: Name of the model

        Returns:
            Dictionary with model status information
        """
        return {
            "loaded": model_name in self.loaded_models,
            "has_error": model_name in self.model_errors,
            "error": self.model_errors.get(model_name),
            "model": self.loaded_models.get(model_name)
        }

    def handle_model_loading_error(self, model_name: str, error: Exception) -> None:
        """
        Handle and log model loading errors.

        Args:
            model_name: Name of the model that failed to load
            error: The exception that was raised
        """
        error_msg = str(error)
        error_type = type(error).__name__

        logger.error(f"Failed to load model '{model_name}': {error_type}: {error_msg}")
        logger.debug(f"Full traceback:\n{traceback.format_exc()}")

        self.model_errors[model_name] = {
            "error_type": error_type,
            "message": error_msg,
            "traceback": traceback.format_exc()
        }

    def log_model_loading_attempt(self, model_name: str, model_path: str, model_config: dict = None) -> None:
        """
        Log model loading attempt with configuration details.

        Args:
            model_name: Name of the model
            model_path: Path to the model file
            model_config: Model configuration
        """
        logger.info(f"Loading model: {model_name}")
        logger.info(f"  Path: {model_path}")

        if model_config:
            logger.debug(f"  Config: {model_config}")


def safe_model_create(create_func, model_name: str, *args, **kwargs) -> Optional[Any]:
    """
    Safely create a model with error logging and recovery.

    Args:
        create_func: Function to create the model
        model_name: Name of the model being created
        *args: Positional arguments for create_func
        **kwargs: Keyword arguments for create_func

    Returns:
        Created model or None if creation failed
    """
    logger.info(f"Creating model: {model_name}")

    try:
        model = create_func(*args, **kwargs)
        logger.info(f"Successfully created model: {model_name}")
        return model
    except Exception as e:
        logger.error(f"Failed to create model '{model_name}': {str(e)}")
        logger.debug(traceback.format_exc())
        return None

