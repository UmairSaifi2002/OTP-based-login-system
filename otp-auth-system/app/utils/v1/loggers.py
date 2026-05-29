"""
Logging Configuration

Sets up structured logging for the entire application.
All modules import this logger for consistent output.
"""

import logging
import sys

def setup_logger(name: str = 'otp_login_system') -> logging.Logger:
    """
    Create and configure a logger.
    
    Output format:
    2026-05-17 14:30:22 - otp_login_system - INFO - Message here
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Prevent Duplicate Handlers
    if logger.handlers:
        return logger
    
    # Console Handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    
    # Console Handler
    formatter = logging.Formatter(
        fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt = "%Y-%m-%d %H:%M:%S",
    )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# Create default logger instance
logger = setup_logger()














