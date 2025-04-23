import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def setup_logging(log_level=logging.INFO, log_file=None):
    """
    Configure the logging system for the application.
    
    Args:
        log_level: The minimum log level to capture
        log_file: Optional path to a log file
    
    Returns:
        The configured logger
    """
    # Create a custom logger
    logger = logging.getLogger("rama")
    logger.setLevel(log_level)
    logger.propagate = False  # Prevent propagating to root logger
    
    # Clear existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    
    # Create formatters
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log file is specified
    if log_file:
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Add rotating file handler
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10485760, backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name):
    """
    Get a logger with the specified name.
    
    Args:
        name: The name for the logger
        
    Returns:
        A configured logger instance
    """
    return logging.getLogger(f"rama.{name}") 