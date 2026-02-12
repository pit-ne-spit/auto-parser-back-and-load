"""Logging configuration module."""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from app.utils.config import config


def setup_logger(name: str = "auto_parser", log_file: Optional[str] = None) -> logging.Logger:
    """
    Setup and configure logger.
    
    Args:
        name: Logger name
        log_file: Path to log file (if None, uses config)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.get('logging.level', 'INFO')))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Get logging configuration
    log_config = config.get_logging_config()
    log_format = log_config.get('format', '[%(levelname)s] %(message)s')
    formatter = logging.Formatter(log_format)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file is None:
        log_file = log_config.get('file_path', 'logs/app.log')
    
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Rotating file handler
    max_bytes = log_config.get('rotation', {}).get('max_bytes', 10485760)  # 10 MB default
    backup_count = log_config.get('rotation', {}).get('backup_count', 5)
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Clean old log files
    cleanup_old_logs(log_path.parent, log_config.get('retention_days', 7))
    
    return logger


def cleanup_old_logs(log_dir: Path, retention_days: int) -> None:
    """
    Remove log files older than retention_days.
    
    Args:
        log_dir: Directory with log files
        retention_days: Number of days to retain logs
    """
    if not log_dir.exists():
        return
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    for log_file in log_dir.glob('*.log*'):
        try:
            # Check file modification time
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff_date:
                log_file.unlink()
                logger = logging.getLogger("auto_parser")
                logger.debug(f"Deleted old log file: {log_file}")
        except Exception as e:
            logger = logging.getLogger("auto_parser")
            logger.warning(f"Failed to delete old log file {log_file}: {e}")


# Create default logger instance
logger = setup_logger()
