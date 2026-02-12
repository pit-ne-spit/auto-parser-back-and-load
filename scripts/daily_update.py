"""Script for daily data updates."""

import asyncio
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.loaders.daily_updater import DailyUpdater
from app.utils.logger import logger
from app.utils.single_instance import SingleInstance


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Daily data update from CHE168 API')
    parser.add_argument(
        '--max-dates',
        type=int,
        default=None,
        help='Maximum number of dates to process (for testing). Default: unlimited'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        default=None,
        help='Start date for processing (format: YYYY-MM-DD). Default: yesterday'
    )
    
    args = parser.parse_args()
    
    # Parse start_date if provided
    start_date = None
    if args.start_date:
        try:
            from datetime import datetime
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        except ValueError:
            logger.error(f"Invalid date format: {args.start_date}. Use YYYY-MM-DD format")
            return 1
    
    # Check for single instance
    with SingleInstance("daily_update"):
        try:
            logger.info("=" * 60)
            logger.info("Starting daily data update")
            if args.max_dates:
                logger.info(f"TEST MODE: Limited to {args.max_dates} date(s)")
            if start_date:
                logger.info(f"Start date specified: {start_date}")
            logger.info("=" * 60)
            
            updater = DailyUpdater(max_dates=args.max_dates, start_date=start_date)
            stats = await updater.update()
            
            logger.info("=" * 60)
            logger.info("Daily update completed!")
            logger.info(f"Statistics:")
            logger.info(f"  - Dates processed: {stats['dates_processed']}")
            logger.info(f"  - Records loaded (new): {stats['total_loaded']}")
            logger.info(f"  - Records updated: {stats['total_updated']}")
            logger.info(f"  - Records removed: {stats['total_removed']}")
            logger.info(f"  - Records duplicates (skipped): {stats.get('total_duplicates', 0)}")
            logger.info(f"  - Errors: {stats['total_errors']}")
            logger.info("=" * 60)
            
            return 0
            
        except KeyboardInterrupt:
            logger.warning("Interrupted by user")
            return 1
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
