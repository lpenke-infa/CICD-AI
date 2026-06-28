"""
Utility functions for IICS CI/CD automation
"""
import time
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

            wait_time = backoff_factor ** attempt
            if logger:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {wait_time}s...")
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
    Validate required fields in input configuration

    Args:
        input_data: Configuration dictionary
        logger: Logger instance

    Returns:
        True if valid, raises Exception otherwise
    """
    required_fields = [
        'ProjectName',
        'IICS_SRC_username', 'IICS_SRC_password', 'IICS_SRC_region',
        'IICS_TGT_username', 'IICS_TGT_password', 'IICS_TGT_region',
        'PreMigration_Tag', 'PostMigration_Tag',
        'Git_Repository_URL', 'Git_config_useremail', 'Git_config_username',
        'Git_password', 'Git_SRC_Branch', 'Git_TGT_Branch',
        'Publish', 'logFileDir'
    ]

    missing_fields = [field for field in required_fields if field not in input_data]

    if missing_fields:
        error_msg = f"Missing required fields in configuration: {', '.join(missing_fields)}"
        logger.critical(error_msg)
        raise ValueError(error_msg)

    if not isinstance(input_data['ProjectName'], list) or len(input_data['ProjectName']) == 0:
        error_msg = "ProjectName must be a non-empty list"
        logger.critical(error_msg)
        raise ValueError(error_msg)

    if not isinstance(input_data['PreMigration_Tag'], list) or len(input_data['PreMigration_Tag']) == 0:
        error_msg = "PreMigration_Tag must be a non-empty list"
        logger.critical(error_msg)
        raise ValueError(error_msg)

    if not isinstance(input_data['PostMigration_Tag'], list) or len(input_data['PostMigration_Tag']) == 0:
        error_msg = "PostMigration_Tag must be a non-empty list"
        logger.critical(error_msg)
        raise ValueError(error_msg)

    logger.info("Input configuration validation successful")
    return True
