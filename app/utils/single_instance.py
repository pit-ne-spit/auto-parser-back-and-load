"""Single instance lock to prevent multiple processes from running simultaneously."""

import os
import sys
import atexit
from pathlib import Path
from typing import Optional

from app.utils.logger import logger


class SingleInstanceLock:
    """Lock to ensure only one instance of a script runs at a time."""
    
    def __init__(self, lock_name: str):
        """
        Initialize single instance lock.
        
        Args:
            lock_name: Unique name for the lock (e.g., 'initial_load', 'daily_update')
        """
        self.lock_name = lock_name
        self.lock_file = Path(__file__).parent.parent.parent / "tmp" / f"{lock_name}.lock"
        self.lock_file.parent.mkdir(exist_ok=True)
        self._locked = False
    
    def acquire(self) -> bool:
        """
        Acquire lock. Returns True if successful, False if another instance is running.
        
        Returns:
            True if lock acquired, False if another instance is running
        """
        if self.lock_file.exists():
            # Check if process is still running
            try:
                pid = int(self.lock_file.read_text().strip())
                # Check if process exists (Windows)
                if sys.platform == 'win32':
                    import psutil
                    if psutil.pid_exists(pid):
                        logger.error(
                            f"Another instance of {self.lock_name} is already running "
                            f"(PID: {pid}). Please wait for it to finish or stop it manually."
                        )
                        return False
                else:
                    # Unix/Linux
                    try:
                        os.kill(pid, 0)  # Check if process exists
                        logger.error(
                            f"Another instance of {self.lock_name} is already running "
                            f"(PID: {pid}). Please wait for it to finish or stop it manually."
                        )
                        return False
                    except OSError:
                        # Process doesn't exist, remove stale lock file
                        self.lock_file.unlink()
            except (ValueError, FileNotFoundError):
                # Invalid lock file, remove it
                self.lock_file.unlink()
        
        # Create lock file with current PID
        try:
            self.lock_file.write_text(str(os.getpid()))
            self._locked = True
            
            # Register cleanup function
            atexit.register(self.release)
            
            logger.debug(f"Lock acquired for {self.lock_name} (PID: {os.getpid()})")
            return True
        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            return False
    
    def release(self) -> None:
        """Release lock."""
        if self._locked and self.lock_file.exists():
            try:
                self.lock_file.unlink()
                self._locked = False
                logger.debug(f"Lock released for {self.lock_name}")
            except Exception as e:
                logger.warning(f"Failed to release lock: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        if not self.acquire():
            sys.exit(1)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()


# Fallback implementation without psutil dependency
class SimpleSingleInstanceLock:
    """Simple lock without process checking (for systems without psutil)."""
    
    def __init__(self, lock_name: str):
        """
        Initialize simple single instance lock.
        
        Args:
            lock_name: Unique name for the lock
        """
        self.lock_name = lock_name
        self.lock_file = Path(__file__).parent.parent.parent / "tmp" / f"{lock_name}.lock"
        self.lock_file.parent.mkdir(exist_ok=True)
        self._locked = False
    
    def acquire(self) -> bool:
        """
        Acquire lock. Returns True if successful, False if lock file exists.
        
        Returns:
            True if lock acquired, False if another instance might be running
        """
        if self.lock_file.exists():
            logger.error(
                f"Lock file exists for {self.lock_name}. "
                f"Another instance might be running. "
                f"If you're sure no other instance is running, delete: {self.lock_file}"
            )
            return False
        
        try:
            self.lock_file.write_text(str(os.getpid()))
            self._locked = True
            atexit.register(self.release)
            logger.debug(f"Lock acquired for {self.lock_name} (PID: {os.getpid()})")
            return True
        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            return False
    
    def release(self) -> None:
        """Release lock."""
        if self._locked and self.lock_file.exists():
            try:
                self.lock_file.unlink()
                self._locked = False
                logger.debug(f"Lock released for {self.lock_name}")
            except Exception as e:
                logger.warning(f"Failed to release lock: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        if not self.acquire():
            sys.exit(1)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()


# Try to use SingleInstanceLock with psutil, fallback to SimpleSingleInstanceLock
try:
    import psutil
    SingleInstance = SingleInstanceLock
except ImportError:
    SingleInstance = SimpleSingleInstanceLock
