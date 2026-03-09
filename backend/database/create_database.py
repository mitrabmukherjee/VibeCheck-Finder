"""
Create the semantic_media database if it doesn't exist.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

def create_database():
    """Create the semantic_media database if it doesn't exist."""
    
    # Connect to PostgreSQL server (default postgres database)
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database="postgres",  # Connect to default database
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "")
    )
    
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Check if database exists
    db_name = os.getenv("POSTGRES_DB", "semantic_media")
    cursor.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (db_name,)
    )
    
    if cursor.fetchone():
        print(f"✓ Database '{db_name}' already exists")
    else:
        # Create database
        cursor.execute(f"CREATE DATABASE {db_name}")
        print(f"✓ Created database '{db_name}'")
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    try:
        create_database()
    except Exception as e:
        print(f"✗ Error: {e}")
        exit(1)
