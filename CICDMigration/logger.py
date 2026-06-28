"""
Logger configuration for IICS CI/CD automation
"""
import os
import logging
from datetime import datetime


def create_logger(log_dir: str, log_level: int = logging.INFO) -> logging.Logger:
    """
    Create and configure a logger instance

    Args:
        log_dir: Directory path for log files
        log_level: Logging level (default: logging.INFO)

    Returns:
        Configured logger instance
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    log_filename = 'CICDMigration.log'

    logger = logging.getLogger('CICDMigration')

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.propagate = False
    logger.setLevel(log_level)

    # File handler with append mode
    file_handler = logging.FileHandler(
        os.path.join(log_dir, log_filename),
        mode='a',
        encoding='utf-8'
    )
    stream_handler = logging.StreamHandler()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    file_handler.setLevel(log_level)
    stream_handler.setLevel(log_level)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    logger.info("="*80)
    logger.info(f"CICD Migration Session Started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)

    return logger
