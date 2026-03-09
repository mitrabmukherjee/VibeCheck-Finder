"""
Database migration script for Semantic Media Engine

This script sets up the PostgreSQL schema for media metadata storage.
It can be run to initialize the database or reset it if needed.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_db_connection():
    """
    Create and return a PostgreSQL database connection.
    
    Returns:
        psycopg2.connection: Database connection object
    
    Raises:
        psycopg2.Error: If connection fails
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DB", "semantic_media"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "")
        )
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        raise


def run_migration(conn, schema_path: Path):
    """
    Execute the SQL schema file to create tables and indexes.
    
    Args:
        conn: PostgreSQL connection object
        schema_path: Path to the schema.sql file
    
    Raises:
        FileNotFoundError: If schema file doesn't exist
        psycopg2.Error: If SQL execution fails
    """
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    cursor = conn.cursor()
    try:
        print("Executing schema migration...")
        cursor.execute(schema_sql)
        conn.commit()
        print("✓ Schema migration completed successfully")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        cursor.close()


def verify_schema(conn):
    """
    Verify that the schema was created correctly.
    
    Args:
        conn: PostgreSQL connection object
    
    Returns:
        bool: True if schema is valid, False otherwise
    """
    cursor = conn.cursor()
    try:
        # Check if media_items table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'media_items'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("✗ Verification failed: media_items table not found")
            return False
        
        # Check if indexes exist
        cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'media_items';
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        
        expected_indexes = [
            'media_items_pkey',  # Primary key index
            'idx_media_items_id',
            'idx_media_items_media_type',
            'idx_media_items_metadata',
            'idx_media_items_created_at'
        ]
        
        missing_indexes = [idx for idx in expected_indexes if idx not in indexes]
        if missing_indexes:
            print(f"✗ Verification failed: Missing indexes: {missing_indexes}")
            return False
        
        # Check if media_type_enum exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_type 
                WHERE typname = 'media_type_enum'
            );
        """)
        enum_exists = cursor.fetchone()[0]
        
        if not enum_exists:
            print("✗ Verification failed: media_type_enum not found")
            return False
        
        print("✓ Schema verification passed")
        return True
        
    except psycopg2.Error as e:
        print(f"✗ Verification error: {e}")
        return False
    finally:
        cursor.close()


def drop_schema(conn):
    """
    Drop all tables and types (use with caution).
    
    Args:
        conn: PostgreSQL connection object
    """
    cursor = conn.cursor()
    try:
        print("Dropping existing schema...")
        cursor.execute("DROP TABLE IF EXISTS media_items CASCADE;")
        cursor.execute("DROP TYPE IF EXISTS media_type_enum CASCADE;")
        cursor.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;")
        conn.commit()
        print("✓ Schema dropped successfully")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"✗ Drop failed: {e}")
        raise
    finally:
        cursor.close()


def main():
    """
    Main migration function.
    
    Usage:
        python migrate.py              # Run migration
        python migrate.py --reset      # Drop and recreate schema
        python migrate.py --verify     # Verify schema only
    """
    # Determine script directory
    script_dir = Path(__file__).parent
    schema_path = script_dir / "schema.sql"
    
    # Parse command line arguments
    reset = "--reset" in sys.argv
    verify_only = "--verify" in sys.argv
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = get_db_connection()
        print("✓ Connected successfully")
        
        if verify_only:
            # Only verify schema
            verify_schema(conn)
        elif reset:
            # Drop and recreate schema
            drop_schema(conn)
            run_migration(conn, schema_path)
            verify_schema(conn)
        else:
            # Run migration
            run_migration(conn, schema_path)
            verify_schema(conn)
        
        conn.close()
        print("\nMigration completed successfully!")
        
    except Exception as e:
        print(f"\nMigration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
