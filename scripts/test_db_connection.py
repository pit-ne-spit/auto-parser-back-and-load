"""Test database connection script."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
from app.utils.config import env_config

async def test_connection():
    """Test database connection."""
    db_config = env_config.get_db_config()
    
    print("Testing database connection...")
    print(f"Host: {db_config['host']}")
    print(f"Port: {db_config['port']}")
    print(f"User: {db_config['user']}")
    print(f"Database: {db_config['database']}")
    print()
    
    try:
        conn = await asyncpg.connect(
            host=db_config['host'],
            port=int(db_config['port']),
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        
        # Test query
        version = await conn.fetchval('SELECT version()')
        print("[SUCCESS] Connection successful!")
        print(f"PostgreSQL version: {version}")
        print()
        
        # List databases
        databases = await conn.fetch("""
            SELECT datname FROM pg_database 
            WHERE datistemplate = false
            ORDER BY datname
        """)
        print("Available databases:")
        for db in databases:
            print(f"  - {db['datname']}")
        
        await conn.close()
        
    except asyncpg.exceptions.InvalidPasswordError:
        print("[ERROR] Invalid password")
        print("Please check your DB_PASSWORD in .env file")
    except asyncpg.exceptions.InvalidCatalogNameError:
        print(f"[ERROR] Database '{db_config['database']}' does not exist")
        print("Available databases listed above")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        print("\nTrying to connect to 'postgres' database...")
        
        # Try default 'postgres' database
        try:
            conn = await asyncpg.connect(
                host=db_config['host'],
                port=int(db_config['port']),
                user=db_config['user'],
                password=db_config['password'],
                database='postgres'
            )
            print("[SUCCESS] Connection to 'postgres' database successful!")
            version = await conn.fetchval('SELECT version()')
            print(f"PostgreSQL version: {version}")
            
            # List databases
            databases = await conn.fetch("""
                SELECT datname FROM pg_database 
                WHERE datistemplate = false
                ORDER BY datname
            """)
            print("\nAvailable databases:")
            for db in databases:
                print(f"  - {db['datname']}")
            
            await conn.close()
        except Exception as e2:
            print(f"[ERROR] Connection to 'postgres' also failed: {e2}")

if __name__ == "__main__":
    asyncio.run(test_connection())
