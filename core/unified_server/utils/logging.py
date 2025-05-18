"""
Logging utilities for Blender GraphQL MCP unified server.
Provides centralized logging configuration and helper functions.
"""

import os
import sys
import logging
import datetime
from typing import Optional, Union, Dict, Any

# Create a default logger
logger = logging.getLogger("blender_mcp")


def setup_logging(
    log_level: Union[str, int] = logging.INFO,
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    log_dir: Optional[str] = None,
    log_file: Optional[str] = None,
    console: bool = True
) -> logging.Logger:
    """
    Configure logging for the server.
    
    Args:
        log_level: Logging level (e.g., DEBUG, INFO, WARNING, ERROR)
        log_format: Format for log messages
        log_dir: Directory for log files. If None, logs to console only
        log_file: Specific log file name. If None, a default name with timestamp is used
        console: Whether to output logs to console
        
    Returns:
        Configured logger
    """
    # Reset handlers to avoid duplicate logs
    logger.handlers = []
    
    # Convert string log level to numeric if necessary
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Set base logger level
    logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Add file handler if log_dir is specified
    if log_dir:
        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Generate log file name if not provided
        if not log_file:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"blender_mcp_server_{timestamp}.log"
            
        # Ensure log_file is a full path
        log_path = os.path.join(log_dir, log_file)
        
        # Create file handler
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"Logging to file: {log_path}")
    
    logger.info(f"Logging initialized at level {logging.getLevelName(log_level)}")
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with the specified name.
    If name is None, returns the root MCP logger.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    if name is None:
        return logger
    
    return logging.getLogger(f"blender_mcp.{name}")


class LogCapture:
    """
    Context manager to capture logs for a specific operation.
    Useful for returning logs as part of API responses.
    """
    
    def __init__(self, logger_name: Optional[str] = None, level: int = logging.INFO):
        self.logger_name = logger_name
        self.level = level
        self.captured_logs = []
        self.handler = None
    
    def __enter__(self):
        # Create a handler that will capture logs
        self.handler = CaptureHandler(self.captured_logs)
        self.handler.setLevel(self.level)
        
        # Get the appropriate logger
        if self.logger_name:
            self.logger = logging.getLogger(self.logger_name)
        else:
            self.logger = logger
        
        # Add the handler
        self.logger.addHandler(self.handler)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Remove the handler
        if self.handler:
            self.logger.removeHandler(self.handler)
    
    def get_logs(self) -> str:
        """Get captured logs as a single string."""
        return "\n".join(self.captured_logs)
    
    def get_log_list(self) -> list:
        """Get captured logs as a list of strings."""
        return self.captured_logs


class CaptureHandler(logging.Handler):
    """Handler to capture log messages in a list."""
    
    def __init__(self, log_list):
        super().__init__()
        self.log_list = log_list
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_list.append(msg)
        except Exception:
            self.handleError(record)