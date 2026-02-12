"""Comprehensive test script for initial load and daily update."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logger import logger
from app.utils.config import env_config
from app.database.connection import AsyncSessionLocal
from app.database.models import RawData, SyncState
from sqlalchemy import select, func
from datetime import date, timedelta


async def check_database():
    """Check database connection and tables."""
    logger.info("=" * 60)
    logger.info("Checking database connection and tables...")
    logger.info("=" * 60)
    
    try:
        async with AsyncSessionLocal() as session:
            # Check if tables exist
            result = await session.execute(
                select(func.count()).select_from(RawData)
            )
            raw_count = result.scalar()
            
            result = await session.execute(
                select(func.count()).select_from(SyncState)
            )
            sync_count = result.scalar()
            
            logger.info(f"✓ Database connection successful")
            logger.info(f"✓ RawData table: {raw_count} records")
            logger.info(f"✓ SyncState table: {sync_count} records")
            
            # Check for unprocessed records
            result = await session.execute(
                select(func.count()).where(RawData.is_processed == False)
            )
            unprocessed = result.scalar()
            logger.info(f"✓ Unprocessed records: {unprocessed}")
            
            return True
            
    except Exception as e:
        logger.error(f"✗ Database check failed: {e}")
        return False


async def test_initial_load(pages: int = 2):
    """Test initial load with limited pages."""
    logger.info("=" * 60)
    logger.info(f"Testing initial load (max {pages} pages)...")
    logger.info("=" * 60)
    
    try:
        from app.loaders.initial_loader import InitialLoader
        
        loader = InitialLoader(max_pages=pages)
        stats = await loader.load()
        
        logger.info("=" * 60)
        logger.info("Initial load test completed!")
        logger.info(f"Statistics:")
        logger.info(f"  - Pages processed: {stats['total_pages']}")
        logger.info(f"  - Records loaded: {stats['total_loaded']}")
        logger.info(f"  - Records skipped (duplicates): {stats['total_skipped']}")
        logger.info(f"  - Errors: {stats['total_errors']}")
        logger.info("=" * 60)
        
        return stats['total_errors'] == 0
        
    except Exception as e:
        logger.error(f"Initial load test failed: {e}", exc_info=True)
        return False


async def test_daily_update(max_dates: int = 1):
    """Test daily update with limited dates."""
    logger.info("=" * 60)
    logger.info(f"Testing daily update (max {max_dates} date(s))...")
    logger.info("=" * 60)
    
    try:
        from app.loaders.daily_updater import DailyUpdater
        
        updater = DailyUpdater(max_dates=max_dates)
        stats = await updater.update()
        
        logger.info("=" * 60)
        logger.info("Daily update test completed!")
        logger.info(f"Statistics:")
        logger.info(f"  - Dates processed: {stats['dates_processed']}")
        logger.info(f"  - Records loaded (new): {stats['total_loaded']}")
        logger.info(f"  - Records updated: {stats['total_updated']}")
        logger.info(f"  - Records removed: {stats['total_removed']}")
        logger.info(f"  - Errors: {stats['total_errors']}")
        logger.info("=" * 60)
        
        return stats['total_errors'] == 0
        
    except Exception as e:
        logger.error(f"Daily update test failed: {e}", exc_info=True)
        return False


async def check_sync_state():
    """Check sync state in database."""
    logger.info("=" * 60)
    logger.info("Checking sync state...")
    logger.info("=" * 60)
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(SyncState))
            sync_states = result.scalars().all()
            
            if sync_states:
                for state in sync_states:
                    logger.info(f"✓ Last successful date: {state.last_successful_date}")
                    logger.info(f"✓ Last change_id: {state.last_change_id}")
                    logger.info(f"✓ Updated at: {state.updated_at}")
            else:
                logger.info("✓ No sync state found (will start from today)")
            
            return True
            
    except Exception as e:
        logger.error(f"Sync state check failed: {e}")
        return False


async def show_summary():
    """Show summary of data in database."""
    logger.info("=" * 60)
    logger.info("Database summary:")
    logger.info("=" * 60)
    
    try:
        async with AsyncSessionLocal() as session:
            # Total records
            result = await session.execute(
                select(func.count()).select_from(RawData)
            )
            total = result.scalar()
            
            # By source
            result = await session.execute(
                select(RawData.source, func.count())
                .group_by(RawData.source)
            )
            by_source = {row[0]: row[1] for row in result.all()}
            
            # By active_status
            result = await session.execute(
                select(RawData.active_status, func.count())
                .group_by(RawData.active_status)
            )
            by_status = {row[0]: row[1] for row in result.all()}
            
            # By is_processed
            result = await session.execute(
                select(RawData.is_processed, func.count())
                .group_by(RawData.is_processed)
            )
            by_processed = {row[0]: row[1] for row in result.all()}
            
            logger.info(f"Total records: {total}")
            logger.info(f"By source: {by_source}")
            logger.info(f"By active_status: {by_status}")
            logger.info(f"By is_processed: {by_processed}")
            
    except Exception as e:
        logger.error(f"Summary failed: {e}")


async def main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("COMPREHENSIVE TEST: Initial Load & Daily Update")
    logger.info("=" * 60)
    
    # Check environment
    logger.info("\n1. Checking environment...")
    api_key = env_config.get_che168_api_key()
    access_name = env_config.get_che168_access_name()
    
    if not api_key:
        logger.error("✗ CHE168_API_KEY not set in .env")
        return 1
    
    if not access_name:
        logger.error("✗ CHE168_ACCESS_NAME not set in .env")
        return 1
    
    logger.info(f"✓ API Key: {'*' * (len(api_key) - 4)}{api_key[-4:]}")
    logger.info(f"✓ Access Name: {access_name}")
    
    # Check database
    logger.info("\n2. Checking database...")
    if not await check_database():
        logger.error("✗ Database check failed. Please check your .env settings and run migrations.")
        return 1
    
    # Show initial summary
    await show_summary()
    
    # Test initial load
    logger.info("\n3. Testing initial load...")
    test_pages = 2  # Test with 2 pages
    if not await test_initial_load(test_pages):
        logger.error("✗ Initial load test failed")
        return 1
    
    # Show summary after initial load
    await show_summary()
    
    # Check sync state
    await check_sync_state()
    
    # Test daily update
    logger.info("\n4. Testing daily update...")
    if not await test_daily_update(max_dates=1):
        logger.error("✗ Daily update test failed")
        return 1
    
    # Final summary
    await show_summary()
    
    logger.info("=" * 60)
    logger.info("ALL TESTS COMPLETED SUCCESSFULLY!")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.warning("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
