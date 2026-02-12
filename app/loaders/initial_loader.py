"""Initial data loader for bulk import."""

import asyncio
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.loaders.base_loader import BaseLoader
from app.database.models import RawData
from app.utils.che168_client import CHE168Client
from app.utils.logger import logger


class InitialLoader(BaseLoader):
    """Loader for initial bulk data import."""
    
    def __init__(self, max_pages: Optional[int] = None):
        """
        Initialize initial loader.
        
        Args:
            max_pages: Maximum number of pages to load (None for unlimited, useful for testing)
        """
        super().__init__("data_fetch")
        self.client = CHE168Client()
        self.max_pages = max_pages
        self.source = "initial_load"
    
    async def load(self) -> Dict[str, Any]:
        """
        Load all offers from API.
        
        Returns:
            Dictionary with statistics: total_loaded, total_errors, total_pages
        """
        await self.start_operation()
        
        stats = {
            'total_loaded': 0,
            'total_errors': 0,
            'total_pages': 0,
            'total_skipped': 0
        }
        
        try:
            page = 1
            has_more = True
            
            # Get first page to determine total (if possible)
            logger.info(f"Starting initial load (max_pages={self.max_pages or 'unlimited'})")
            
            while has_more:
                # Check max_pages limit for testing
                if self.max_pages and page > self.max_pages:
                    logger.info(f"Reached max_pages limit ({self.max_pages}), stopping")
                    break
                
                try:
                    # Rate limiting: wait 0.7 seconds between requests
                    if page > 1:
                        await asyncio.sleep(0.7)
                    
                    # Fetch page from API
                    # Use asyncio.to_thread to avoid blocking event loop with sync API calls
                    response = await asyncio.to_thread(self.client.get_offers, page=page)
                    
                    result = response.get('result', [])
                    meta = response.get('meta', {})
                    next_page = meta.get('next_page')
                    
                    if not result:
                        logger.warning(f"No data in page {page}")
                        has_more = False
                        break
                    
                    # Process and save records
                    loaded, skipped = await self._save_page(result, page)
                    stats['total_loaded'] += loaded
                    stats['total_skipped'] += skipped
                    stats['total_pages'] += 1
                    
                    # Progress output
                    progress_msg = (
                        f'\r[INFO] Initial load: Page {page} | '
                        f'Records loaded: {stats["total_loaded"]:,} | '
                        f'Skipped: {stats["total_skipped"]:,} | '
                        f'Errors: {stats["total_errors"]}'
                    )
                    sys.stdout.write(progress_msg)
                    sys.stdout.flush()
                    
                    # Check if there's a next page
                    if next_page is None:
                        has_more = False
                    else:
                        page = next_page
                    
                except Exception as e:
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                    self.record_error(e, f"page {page}")
                    stats['total_errors'] += 1
                    
                    # Wait 0.7 seconds before retrying next page
                    await asyncio.sleep(0.7)
                    
                    # Continue to next page even on error
                    page += 1
                    # Safety check: if we've had too many errors, stop
                    if stats['total_errors'] > 10:
                        logger.error("Too many errors, stopping load")
                        break
            
            # Finish progress line
            sys.stdout.write('\n')
            sys.stdout.flush()
            
            await self.finish_operation(
                "ERROR" if stats['total_errors'] > 0 else "OK"
            )
            
            logger.info(
                f"Initial load completed: "
                f"pages={stats['total_pages']}, "
                f"loaded={stats['total_loaded']}, "
                f"skipped={stats['total_skipped']}, "
                f"errors={stats['total_errors']}"
            )
            
            return stats
            
        except Exception as e:
            self.record_error(e, "initial load")
            await self.finish_operation("ERROR")
            raise
    
    async def _save_page(
        self,
        records: list,
        page: int
    ) -> tuple[int, int]:
        """
        Save page of records to database.
        
        Args:
            records: List of records from API
            page: Page number (for logging)
            
        Returns:
            Tuple of (loaded_count, skipped_count)
        """
        loaded = 0
        skipped = 0
        now = datetime.utcnow()
        
        async with self.get_db_session() as session:
            for record in records:
                try:
                    inner_id = record.get('inner_id')
                    if not inner_id:
                        logger.warning(f"Record without inner_id skipped: {record.get('id')}")
                        skipped += 1
                        continue
                    
                    # Check if record already exists
                    existing = await session.execute(
                        select(RawData).where(RawData.inner_id == inner_id)
                    )
                    if existing.scalar_one_or_none():
                        # Duplicate, skip
                        skipped += 1
                        continue
                    
                    # Parse created_at
                    created_at_str = record.get('created_at')
                    if created_at_str:
                        try:
                            # Try parsing ISO format
                            created_at = datetime.fromisoformat(
                                created_at_str.replace('Z', '+00:00')
                            )
                            # Convert to UTC naive datetime
                            if created_at.tzinfo:
                                created_at = created_at.astimezone().replace(tzinfo=None)
                        except Exception:
                            created_at = now
                    else:
                        created_at = now
                    
                    # Create new record
                    raw_data = RawData(
                        inner_id=inner_id,
                        change_type=record.get('change_type', 'added'),
                        created_at=created_at,
                        data=record.get('data', {}),
                        first_loaded_at=now,
                        last_updated_at=now,
                        source=self.source,
                        active_status=0,  # Active by default
                        is_processed=False
                    )
                    
                    session.add(raw_data)
                    loaded += 1
                    
                except Exception as e:
                    self.record_error(e, f"record {record.get('inner_id', 'unknown')}")
                    skipped += 1
            
            # Commit all records from this page
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                self.record_error(e, f"commit page {page}")
                raise
        
        return loaded, skipped
