"""Daily updater for incremental data updates."""

import asyncio
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.loaders.base_loader import BaseLoader
from app.database.models import RawData, SyncState
from app.utils.che168_client import CHE168Client
from app.utils.json_merger import merge_json
from app.utils.logger import logger


class DailyUpdater(BaseLoader):
    """Updater for daily incremental data updates."""
    
    def __init__(self, max_dates: Optional[int] = None, start_date: Optional[date] = None):
        """
        Initialize daily updater.
        
        Args:
            max_dates: Maximum number of dates to process (None for unlimited, useful for testing)
            start_date: Start date for processing (None means today - 1 day)
        """
        super().__init__("data_fetch")
        self.client = CHE168Client()
        self.source = "daily_update"
        self.max_dates = max_dates
        self.start_date = start_date
    
    async def update(self) -> Dict[str, Any]:
        """
        Update data from API changes.
        
        Logic:
        1. Get change_id for date = today - 1 day
        2. Request /changes with change_id
        3. Process changes and get next_change_id from meta
        4. Repeat step 2-3 until next_change_id is null
        
        Returns:
            Dictionary with statistics
        """
        await self.start_operation()
        
        stats = {
            'dates_processed': 0,
            'total_loaded': 0,
            'total_updated': 0,
            'total_removed': 0,
            'total_errors': 0,
            'total_duplicates': 0
        }
        
        try:
            # Get date to process
            if self.start_date:
                process_date = self.start_date
            else:
                # Default: today - 1 day
                today = date.today()
                process_date = today - timedelta(days=1)
            
            # Check if already processed
            async with self.get_db_session() as session:
                result = await session.execute(select(SyncState))
                sync_state = result.scalar_one_or_none()
                
                if sync_state and sync_state.last_successful_date >= process_date:
                    logger.info(f"Date {process_date} already processed (last_date={sync_state.last_successful_date})")
                    await self.finish_operation("OK")
                    return stats
            
            logger.info(f"Processing date: {process_date}")
            
            # Step 1: Get initial change_id for this date
            try:
                change_id_response = await asyncio.to_thread(
                    self.client.get_change_id, 
                    process_date
                )
                
                if not change_id_response:
                    logger.warning(f"No change_id returned for date {process_date}")
                    await self.finish_operation("OK")
                    return stats
                
                # Response format: {"change_id": 123456789}
                # get_change_id returns int directly
                initial_change_id = change_id_response
                
                if not initial_change_id:
                    logger.warning(f"change_id is None for date {process_date}")
                    await self.finish_operation("OK")
                    return stats
                
                logger.info(f"Got initial change_id: {initial_change_id} for date {process_date}")
                
            except Exception as e:
                self.record_error(e, f"get_change_id for {process_date}")
                stats['total_errors'] += 1
                await self.finish_operation("ERROR")
                return stats
            
            # Step 2-3: Process all pages of changes
            current_change_id = initial_change_id
            page_number = 0
            last_change_id = None
            total_records_processed = 0
            
            logger.info("Starting pagination...")
            
            while True:
                page_number += 1
                try:
                    # Rate limiting: wait 2 seconds between requests (1 request per 2 seconds max)
                    if page_number > 1:
                        await asyncio.sleep(2)
                    
                    # Request /changes with current_change_id
                    response = await asyncio.to_thread(
                        self.client.get_changes,
                        change_id=current_change_id
                    )
                    
                    # Extract result and meta
                    result = response.get('result', [])
                    meta = response.get('meta', {})
                    
                    # Get next_change_id from meta
                    next_change_id = meta.get('next_change_id')
                    cur_change_id = meta.get('cur_change_id')
                    
                    # Process records if any
                    if result:
                        page_stats = await self._save_changes(result)
                        stats['total_loaded'] += page_stats.get('loaded', 0)
                        stats['total_updated'] += page_stats.get('updated', 0)
                        stats['total_removed'] += page_stats.get('removed', 0)
                        stats['total_errors'] += page_stats.get('errors', 0)
                        stats['total_duplicates'] += page_stats.get('duplicates', 0)
                        
                        # Update progress
                        total_records_processed += len(result)
                        # Progress output to logs (for VPS monitoring)
                        logger.info(
                            f"Daily update: Page {page_number} | "
                            f"Records: {total_records_processed:,} | "
                            f"Loaded: {stats['total_loaded']:,} | "
                            f"Updated: {stats['total_updated']:,} | "
                            f"Removed: {stats['total_removed']:,} | "
                            f"Duplicates: {stats['total_duplicates']:,}"
                        )
                    
                    # Update last_change_id
                    if cur_change_id:
                        last_change_id = cur_change_id
                    else:
                        last_change_id = current_change_id
                    
                    # Check if there's more pages
                    # Stop when next_change_id is None or null
                    if next_change_id is None:
                        logger.info(f"Pagination complete: processed {page_number} page(s), {total_records_processed} records")
                        break
                    
                    # Continue with next_change_id
                    current_change_id = next_change_id
                    
                except Exception as e:
                    self.record_error(e, f"changes page {page_number} for {process_date}")
                    stats['total_errors'] += 1
                    break
            
            # Update sync_state after successful processing
            if stats['total_errors'] == 0:
                await self._update_sync_state(process_date, last_change_id)
                stats['dates_processed'] = 1
            
            await self.finish_operation(
                "ERROR" if stats['total_errors'] > 0 else "OK"
            )
            
            logger.info(
                f"Daily update completed for {process_date}: "
                f"pages={page_number}, "
                f"loaded={stats['total_loaded']}, "
                f"updated={stats['total_updated']}, "
                f"removed={stats['total_removed']}, "
                f"duplicates={stats['total_duplicates']}, "
                f"errors={stats['total_errors']}"
            )
            
            return stats
            
        except Exception as e:
            self.record_error(e, "daily update")
            await self.finish_operation("ERROR")
            raise
    
    async def _save_changes(self, records: list) -> Dict[str, int]:
        """
        Save changes to database.
        
        Args:
            records: List of change records from API
            
        Returns:
            Statistics dictionary
        """
        stats = {'loaded': 0, 'updated': 0, 'removed': 0, 'errors': 0, 'duplicates': 0}
        now = datetime.utcnow()
        
        async with self.get_db_session() as session:
            for record in records:
                try:
                    inner_id = record.get('inner_id')
                    if not inner_id:
                        logger.warning(f"Record without inner_id skipped: {record.get('id', 'unknown')}")
                        stats['errors'] += 1
                        continue
                    
                    change_type = record.get('change_type', 'added')
                    created_at_str = record.get('created_at')
                    
                    # Parse created_at
                    if created_at_str:
                        try:
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
                    
                    # Check if record exists
                    existing = await session.execute(
                        select(RawData).where(RawData.inner_id == inner_id)
                    )
                    existing_record = existing.scalar_one_or_none()
                    
                    if change_type == "added":
                        if existing_record:
                            # Already exists, skip (duplicate)
                            stats['duplicates'] += 1
                            continue
                        
                        # Create new record
                        raw_data = RawData(
                            inner_id=inner_id,
                            change_type=change_type,
                            created_at=created_at,
                            data=record.get('data', {}),
                            first_loaded_at=now,
                            last_updated_at=now,
                            source=self.source,
                            active_status=0,
                            is_processed=False
                        )
                        session.add(raw_data)
                        stats['loaded'] += 1
                        
                    elif change_type == "changed":
                        if existing_record:
                            # Update existing record
                            existing_data = existing_record.data or {}
                            new_data = record.get('data', {})
                            
                            # Merge JSON with field mapping
                            merged_data = merge_json(existing_data, new_data)
                            
                            existing_record.change_type = change_type
                            existing_record.created_at = created_at
                            existing_record.data = merged_data
                            existing_record.last_updated_at = now
                            existing_record.is_processed = False
                            
                            stats['updated'] += 1
                        else:
                            # Edge case: record doesn't exist, create it
                            raw_data = RawData(
                                inner_id=inner_id,
                                change_type=change_type,
                                created_at=created_at,
                                data=record.get('data', {}),
                                first_loaded_at=now,
                                last_updated_at=now,
                                source=self.source,
                                active_status=0,
                                is_processed=False
                            )
                            session.add(raw_data)
                            stats['loaded'] += 1
                            
                    elif change_type == "removed":
                        if existing_record:
                            # Mark as inactive
                            existing_record.change_type = change_type
                            existing_record.active_status = 1
                            existing_record.last_updated_at = now
                            existing_record.is_processed = False
                            
                            stats['removed'] += 1
                        else:
                            # Edge case: record doesn't exist, create it as inactive
                            raw_data = RawData(
                                inner_id=inner_id,
                                change_type=change_type,
                                created_at=created_at,
                                data={},
                                first_loaded_at=now,
                                last_updated_at=now,
                                source=self.source,
                                active_status=1,
                                is_processed=False
                            )
                            session.add(raw_data)
                            stats['loaded'] += 1
                    
                except Exception as e:
                    self.record_error(e, f"record {record.get('inner_id', 'unknown')}")
                    stats['errors'] += 1
            
            # Commit all changes
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                self.record_error(e, "commit changes")
                raise
        
        return stats
    
    async def _update_sync_state(
        self,
        process_date: date,
        last_change_id: Optional[int]
    ) -> None:
        """
        Update sync_state after successful processing.
        
        Args:
            process_date: Date that was processed
            last_change_id: Last processed change_id
        """
        async with self.get_db_session() as session:
            result = await session.execute(select(SyncState))
            sync_state = result.scalar_one_or_none()
            
            if sync_state:
                # Update existing record
                sync_state.last_successful_date = process_date
                sync_state.last_change_id = last_change_id
                sync_state.updated_at = datetime.utcnow()
            else:
                # Create new record
                sync_state = SyncState(
                    last_successful_date=process_date,
                    last_change_id=last_change_id,
                    updated_at=datetime.utcnow()
                )
                session.add(sync_state)
            
            await session.commit()
