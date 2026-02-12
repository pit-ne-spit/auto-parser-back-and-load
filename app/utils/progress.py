"""Progress bar for console output."""

import sys
import time
from datetime import datetime, timedelta
from typing import Optional

from app.utils.logger import logger


class ProgressBar:
    """Console progress bar."""
    
    def __init__(
        self,
        total: int,
        description: str = "Progress",
        update_interval: float = 1.0
    ):
        """
        Initialize progress bar.
        
        Args:
            total: Total number of items to process
            description: Description text
            update_interval: Minimum interval between updates in seconds
        """
        self.total = total
        self.description = description
        self.update_interval = update_interval
        self.current = 0
        self.start_time = datetime.now()
        self.last_update_time = datetime.now()
        self.last_update_count = 0
    
    def update(self, increment: int = 1) -> None:
        """
        Update progress bar.
        
        Args:
            increment: Number of items processed since last update
        """
        self.current += increment
        
        # Check if enough time has passed for update
        now = datetime.now()
        elapsed = (now - self.last_update_time).total_seconds()
        
        if elapsed >= self.update_interval or self.current >= self.total:
            self._display()
            self.last_update_time = now
            self.last_update_count = self.current
    
    def _display(self) -> None:
        """Display progress bar."""
        if self.total == 0:
            percentage = 0.0
        else:
            percentage = (self.current / self.total) * 100
        
        # Calculate speed (items per minute)
        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        if elapsed_time > 0:
            speed = (self.current / elapsed_time) * 60  # items per minute
        else:
            speed = 0
        
        # Calculate ETA
        if self.current > 0 and self.current < self.total:
            remaining = self.total - self.current
            eta_seconds = (remaining / self.current) * elapsed_time
            eta = timedelta(seconds=int(eta_seconds))
            eta_str = f" | ETA: {eta}"
        else:
            eta_str = ""
        
        # Format progress bar
        bar_length = 50
        filled_length = int(bar_length * self.current / self.total) if self.total > 0 else 0
        bar = '=' * filled_length + '-' * (bar_length - filled_length)
        
        # Format message
        message = (
            f"[INFO] {self.description}: {percentage:.1f}% "
            f"({self.current:,} / {self.total:,} records) "
            f"| Speed: {speed:.0f} records/min{eta_str}"
        )
        
        # Print to console (overwrite previous line)
        sys.stdout.write(f'\r{message}')
        sys.stdout.flush()
        
        # If complete, print newline
        if self.current >= self.total:
            sys.stdout.write('\n')
            sys.stdout.flush()
            logger.info(
                f"{self.description} completed: {self.current:,} records processed in "
                f"{elapsed_time:.0f} seconds"
            )
    
    def finish(self) -> None:
        """Finish progress bar (force final display)."""
        self.current = self.total
        self._display()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.finish()


def format_progress(current: int, total: int, description: str = "Progress") -> str:
    """
    Format progress message without progress bar.
    
    Args:
        current: Current number of processed items
        total: Total number of items
        description: Description text
        
    Returns:
        Formatted progress string
    """
    if total == 0:
        percentage = 0.0
    else:
        percentage = (current / total) * 100
    
    return (
        f"[INFO] {description}: {percentage:.1f}% "
        f"({current:,} / {total:,} records)"
    )
