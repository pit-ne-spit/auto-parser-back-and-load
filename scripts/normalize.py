"""Script for data normalization."""

import asyncio
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.normalizers.data_normalizer import DataNormalizer
from app.utils.logger import logger


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Normalize data from raw_data to processed_data')
    parser.add_argument(
        '--batch-size',
        type=int,
        default=None,
        help='Number of records per batch (default from config)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of records to process (for testing)'
    )
    
    args = parser.parse_args()
    
    try:
        logger.info("=" * 60)
        logger.info("Starting data normalization")
        if args.batch_size:
            logger.info(f"Batch size: {args.batch_size}")
        if args.limit:
            logger.info(f"Limit: {args.limit} records")
        logger.info("=" * 60)
        
        normalizer = DataNormalizer(batch_size=args.batch_size)
        stats = await normalizer.normalize(limit=args.limit)
        
        logger.info("=" * 60)
        logger.info("Normalization completed!")
        logger.info(f"Statistics:")
        logger.info(f"  - Records processed: {stats['total_processed']}")
        logger.info(f"  - Records created: {stats['total_created']}")
        logger.info(f"  - Records updated: {stats['total_updated']}")
        logger.info(f"  - Errors: {stats['total_errors']}")
        logger.info(f"  - Batches: {stats['total_batches']}")
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
