import logging
import sys
from logging.handlers import RotatingFileHandler
from app.core.config import get_settings

# Configure logging
def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance"""
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # Log format following industry standards
    # Includes: timestamp, logger name, level, and message
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)
    
    # Console handler (stdout) - for container logs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


# Pre-configured loggers for different modules
app_logger = get_logger("app")
flag_logger = get_logger("app.flags")
evaluator_logger = get_logger("app.evaluator")
db_logger = get_logger("app.db")
