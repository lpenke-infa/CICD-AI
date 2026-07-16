"""
Utility functions for IICS CI/CD automation
"""
import time
import random
import requests
from typing import Callable, Any, Optional
from .config import MAX_RETRIES, RETRY_BACKOFF_FACTOR, API_TIMEOUT


def retry_with_backoff(
    func: Callable,
    max_retries: int = MAX_RETRIES,
    backoff_factor: int = RETRY_BACKOFF_FACTOR,
    logger: Any = None
) -> Any:
    """
    Retry a function with exponential backoff

    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for backoff delay
        logger: Logger instance for logging retry attempts

    Returns:
        Result of the function call

    Raises:
        Exception: If all retries are exhausted
    """
    for attempt in range(max_retries):
        try:
            return func()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise

            # Exponential backoff with full jitter to avoid a thundering herd
            # when multiple requests retry in lockstep.
            base_wait = backoff_factor ** attempt
            wait_time = random.uniform(0, base_wait)
            if logger:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {wait_time:.2f}s...")
            time.sleep(wait_time)

    raise Exception(f"Failed after {max_retries} attempts")


def sanitize_for_log(text: str) -> str:
    """
    Remove sensitive information from text before logging

    Args:
        text: Text that may contain sensitive information

    Returns:
        Sanitized text safe for logging
    """
    if not text:
        return text

    sanitized = text

    if '@' in sanitized and 'http' in sanitized:
        parts = sanitized.split('@')
        if len(parts) > 1:
            protocol_and_creds = parts[0]
            if '://' in protocol_and_creds:
                protocol = protocol_and_creds.split('://')[0]
                sanitized = f"{protocol}://[REDACTED]@{parts[1]}"

    return sanitized


def validate_input_data(input_data: dict, logger: Any) -> bool:
    """
    Validate configuration using comprehensive modular validation

    Args:
        input_data: Configuration dictionary
        logger: Logger instance

    Returns:
        True if valid, raises Exception otherwise
    """
    try:
        # Use new modular validation
        from common.config_validation import validate_config

        result = validate_config(input_data, config_type='cicd')

        # Log any warnings
        if result['warnings']:
            for warning in result['warnings']:
                logger.warning(warning)

        # Update input_data with validated/normalized values
        input_data.update(result['config'])

        logger.info("Input configuration validation successful")
        return True

    except ValueError as e:
        logger.critical(str(e))
        raise
