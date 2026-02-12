"""Base loader class with common functionality."""

from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.connection import AsyncSessionLocal
from app.database.models import OperationsLog
from app.utils.logger import logger


class BaseLoader:
    """Base class for data loaders."""
    
    def __init__(self, operation_type: str):
        """
        Initialize base loader.
        
        Args:
            operation_type: Type of operation ("data_fetch" or "normalization")
        """
        self.operation_type = operation_type
        self.started_at: Optional[datetime] = None
        self.errors_count = 0
    
    async def start_operation(self) -> None:
        """Start operation and log it."""
        self.started_at = datetime.utcnow()
        logger.info(f"Starting {self.operation_type} operation")
    
    async def finish_operation(self, status: str = "OK") -> None:
        """
        Finish operation and log it.
        
        Args:
            status: Operation status ("OK" or "ERROR")
        """
        if not self.started_at:
            return
        
        duration = int((datetime.utcnow() - self.started_at).total_seconds())
        
        # Determine final status
        if self.errors_count > 0 and status == "OK":
            status = "ERROR"
        
        details = None
        if self.errors_count > 0:
            details = f"Completed with {self.errors_count} errors"
        
        # Save to operations_log
        async with AsyncSessionLocal() as session:
            log_entry = OperationsLog(
                operation_type=self.operation_type,
                started_at=self.started_at,
                duration=duration,
                status=status,
                details=details
            )
            session.add(log_entry)
            await session.commit()
        
        logger.info(
            f"Finished {self.operation_type} operation: "
            f"status={status}, duration={duration}s, errors={self.errors_count}"
        )
    
    def record_error(self, error: Exception, context: Optional[str] = None) -> None:
        """
        Record an error during operation.
        
        Args:
            error: Exception that occurred
            context: Optional context information
        """
        self.errors_count += 1
        error_msg = str(error)
        if context:
            logger.error(f"Error in {context}: {error_msg}")
        else:
            logger.error(f"Error: {error_msg}")
    
    def get_db_session(self):
        """
        Get database session context manager.
        
        Returns:
            AsyncSession context manager
        """
        return AsyncSessionLocal()
