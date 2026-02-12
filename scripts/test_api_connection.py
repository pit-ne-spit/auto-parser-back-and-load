"""Simple API connection test."""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables explicitly
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

from app.utils.che168_client import CHE168Client
from app.utils.config import config
from app.utils.logger import logger


def main():
    """Test API connection."""
    logger.info("=" * 60)
    logger.info("Testing API connection")
    logger.info("=" * 60)
    
    try:
        # Get API credentials from environment (already loaded by config module)
        api_key = os.getenv('CHE168_API_KEY')
        access_name = os.getenv('CHE168_ACCESS_NAME')
        
        logger.info(f"Checking environment variables...")
        logger.info(f"CHE168_API_KEY present: {bool(api_key)}")
        logger.info(f"CHE168_ACCESS_NAME present: {bool(access_name)}")
        
        if not api_key or not access_name:
            logger.error("CHE168_API_KEY or CHE168_ACCESS_NAME not found in environment")
            logger.error("Please check .env file in project root")
            return 1
        
        logger.info(f"API Key: {api_key[:16]}...")
        logger.info(f"Access Name: {access_name}")
        logger.info("")
        
        import requests
        import time
        from datetime import date
        
        # Test 1: /offers endpoint
        logger.info("Test 1: /offers endpoint...")
        url_offers = f"https://{access_name}.auto-parser.ru/api/v2/che168/offers"
        params_offers = {"api_key": api_key, "page": 1}
        
        response_offers = requests.get(url_offers, params=params_offers, timeout=30)
        logger.info(f"Status Code: {response_offers.status_code}")
        
        if response_offers.status_code == 200:
            data_offers = response_offers.json()
            logger.info(f"✓ /offers: Got {len(data_offers.get('data', []))} records")
        else:
            logger.error(f"✗ /offers: Error {response_offers.status_code}")
        
        logger.info("")
        time.sleep(2)  # Wait 2 seconds
        
        # Test 2: /change_id endpoint
        logger.info("Test 2: /change_id endpoint...")
        url_change_id = f"https://{access_name}.auto-parser.ru/api/v2/che168/change_id"
        test_date = "2025-04-30"
        params_change_id = {"api_key": api_key, "process_date": test_date}
        
        response_change_id = requests.get(url_change_id, params=params_change_id, timeout=30)
        logger.info(f"Status Code: {response_change_id.status_code}")
        
        change_id = None
        if response_change_id.status_code == 200:
            data_change_id = response_change_id.json()
            change_id = data_change_id.get('data', {}).get('change_id')
            logger.info(f"✓ /change_id: Got change_id={change_id} for {test_date}")
        else:
            logger.error(f"✗ /change_id: Error {response_change_id.status_code}")
        
        if not change_id:
            logger.warning("Cannot test /changes endpoint without change_id")
            return 0
        
        logger.info("")
        time.sleep(2)  # Wait 2 seconds
        
        # Test 3: /changes endpoint
        logger.info("Test 3: /changes endpoint...")
        url_changes = f"https://{access_name}.auto-parser.ru/api/v2/che168/changes"
        params_changes = {"api_key": api_key, "change_id": change_id}
        
        response_changes = requests.get(url_changes, params=params_changes, timeout=30)
        logger.info(f"Status Code: {response_changes.status_code}")
        
        if response_changes.status_code == 200:
            data_changes = response_changes.json()
            logger.info(f"✓ /changes: Success!")
            logger.info(f"  Response keys: {list(data_changes.keys())}")
            if 'data' in data_changes:
                logger.info(f"  Data keys: {list(data_changes.get('data', {}).keys())}")
        else:
            logger.error(f"✗ /changes: Error {response_changes.status_code}")
            logger.error(f"  Response: {response_changes.text[:500]}")
            
    except Exception as e:
        logger.error(f"Connection error: {e}", exc_info=True)
        return 1
        
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
