"""Script for initial data loading."""

import asyncio
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.loaders.initial_loader import InitialLoader
from app.utils.logger import logger
from app.utils.single_instance import SingleInstance


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Initial data load from CHE168 API')
    parser.add_argument(
        '--max-pages',
        type=int,
        default=None,
        help='Maximum number of pages to load (for testing). Default: unlimited'
    )
    
    args = parser.parse_args()
    
    # Check for single instance
    with SingleInstance("initial_load"):
        try:
            logger.info("=" * 60)
            logger.info("Starting initial data load")
            if args.max_pages:
                logger.info(f"TEST MODE: Limited to {args.max_pages} pages")
            logger.info("=" * 60)
            
            loader = InitialLoader(max_pages=args.max_pages)
            stats = await loader.load()
            
            logger.info("=" * 60)
            logger.info("Initial load completed successfully!")
            logger.info(f"Statistics:")
            logger.info(f"  - Pages processed: {stats['total_pages']}")
            logger.info(f"  - Records loaded: {stats['total_loaded']}")
            logger.info(f"  - Records skipped (duplicates): {stats['total_skipped']}")
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
