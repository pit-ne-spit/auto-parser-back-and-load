"""Check sync state to see which date will be processed."""

import asyncio
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import AsyncSessionLocal
from app.database.models import SyncState
from sqlalchemy import select


async def main():
    """Check sync state."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SyncState))
        state = result.scalar_one_or_none()
        
        today = date.today()
        process_date = today - timedelta(days=1)
        
        print("=" * 60)
        print("Sync State Information:")
        print("=" * 60)
        if state:
            print(f"Last successful date: {state.last_successful_date}")
            print(f"Last change_id: {state.last_change_id}")
            print(f"Updated at: {state.updated_at}")
        else:
            print("No sync state found (first run)")
        
        print("-" * 60)
        print(f"Today: {today}")
        print(f"Will process date: {process_date}")
        
        if state and state.last_successful_date >= process_date:
            print(f"Status: Date {process_date} already processed")
        else:
            print(f"Status: Will process date {process_date}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
