"""Script for daily data updates."""

import asyncio
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.loaders.daily_updater import DailyUpdater
from app.normalizers.data_normalizer import DataNormalizer
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
    parser.add_argument(
        '--skip-normalization',
        action='store_true',
        help='Skip automatic normalization after update (default: normalization runs automatically)'
    )
    parser.add_argument(
        '--normalization-batch-size',
        type=int,
        default=None,
        help='Batch size for normalization (default from config)'
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
            
            # Determine if update was successful
            # Consider successful if no errors or if we processed at least some records
            update_successful = (
                stats['total_errors'] == 0 or 
                (stats['total_loaded'] + stats['total_updated'] + stats['total_removed']) > 0
            )
            
            # Auto-normalization after successful update
            if update_successful and not args.skip_normalization:
                logger.info("=" * 60)
                logger.info("Starting automatic normalization...")
                logger.info("=" * 60)
                
                try:
                    normalizer = DataNormalizer(batch_size=args.normalization_batch_size)
                    normalization_stats = await normalizer.normalize()
                    
                    logger.info("=" * 60)
                    logger.info("Automatic normalization completed!")
                    logger.info(f"Statistics:")
                    logger.info(f"  - Records processed: {normalization_stats['total_processed']}")
                    logger.info(f"  - Records created: {normalization_stats['total_created']}")
                    logger.info(f"  - Records updated: {normalization_stats['total_updated']}")
                    logger.info(f"  - Errors: {normalization_stats['total_errors']}")
                    logger.info(f"  - Batches: {normalization_stats['total_batches']}")
                    logger.info("=" * 60)
                    
                    # Return error code if normalization had errors
                    if normalization_stats['total_errors'] > 0:
                        logger.warning("Normalization completed with errors")
                        return 1
                    
                except Exception as e:
                    logger.error(f"Error during automatic normalization: {e}", exc_info=True)
                    logger.warning("Daily update completed, but normalization failed")
                    return 1
            elif args.skip_normalization:
                logger.info("Normalization skipped (--skip-normalization flag)")
            elif not update_successful:
                logger.warning("Update had errors, skipping normalization")
                return 1
            
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
