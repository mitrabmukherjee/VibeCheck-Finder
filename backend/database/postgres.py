"""
PostgreSQL database interface for media metadata storage.

This module provides functions for interacting with the media_items table,
including CRUD operations and metadata queries.
"""

import os
import uuid
import time
from typing import List, Dict, Any, Optional, Callable, TypeVar
from datetime import datetime
from urllib.parse import urlparse
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, execute_batch
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()

T = TypeVar('T')


class PostgresDatabase:
    """Interface for PostgreSQL media metadata storage with connection pooling and retry logic."""
    
    def __init__(self, min_connections: int = 1, max_connections: int = 10):
        """
        Initialize database connection pool.
        
        Uses DATABASE_URL if set (e.g. Render, Heroku), otherwise POSTGRES_HOST, etc.
        
        Args:
            min_connections: Minimum number of connections in the pool
            max_connections: Maximum number of connections in the pool
        """
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            # Use full connection string with SSL required (e.g., Render internal URL)
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                min_connections,
                max_connections,
                database_url,
                sslmode="require"
            )
            self.connection_params = {"dsn": database_url, "sslmode": "require"}
        else:
            self.connection_params = {
                "host": os.getenv("POSTGRES_HOST", "localhost"),
                "port": os.getenv("POSTGRES_PORT", "5432"),
                "database": os.getenv("POSTGRES_DB", "semantic_media"),
                "user": os.getenv("POSTGRES_USER", "postgres"),
                "password": os.getenv("POSTGRES_PASSWORD", "")
            }
            # Initialize connection pool with discrete params
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                min_connections,
                max_connections,
                **self.connection_params
            )
    
    def _get_connection(self):
        """Get a connection from the pool."""
        return self.pool.getconn()
    
    def _put_connection(self, conn):
        """Return a connection to the pool."""
        self.pool.putconn(conn)
    
    def _retry_on_failure(
        self, 
        operation: Callable[[], T], 
        max_retries: int = 3, 
        retry_delay: float = 0.5
    ) -> T:
        """
        Execute a database operation with retry logic.
        
        Args:
            operation: Function to execute
            max_retries: Maximum number of retry attempts
            retry_delay: Delay in seconds between retries
        
        Returns:
            Result of the operation
        
        Raises:
            psycopg2.Error: If all retry attempts fail
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return operation()
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                raise
            except psycopg2.Error:
                # Don't retry on other database errors (e.g., constraint violations)
                raise
        
        # This should never be reached, but just in case
        if last_error:
            raise last_error
    
    def close(self):
        """Close all connections in the pool."""
        if self.pool:
            self.pool.closeall()
    
    def insert_media(self, media: Dict[str, Any]) -> str:
        """
        Insert a new media item into the database.
        
        Args:
            media: Dictionary containing media fields:
                - id (optional): UUID string, generated if not provided
                - title: Media title (required, max 500 chars)
                - description: Media description (required)
                - media_type: Either 'book' or 'tv_show' (required)
                - metadata: Additional metadata as dict (optional)
        
        Returns:
            str: The UUID of the inserted media item
        
        Raises:
            ValueError: If required fields are missing or invalid
            psycopg2.Error: If database operation fails
        """
        # Validate required fields
        if not media.get("title"):
            raise ValueError("title is required")
        if not media.get("description"):
            raise ValueError("description is required")
        if media.get("media_type") not in ["book", "tv_show"]:
            raise ValueError("media_type must be 'book' or 'tv_show'")
        
        # Generate UUID if not provided
        media_id = media.get("id", str(uuid.uuid4()))
        
        def _insert():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    """
                    INSERT INTO media_items (id, title, description, media_type, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        media_id,
                        media["title"],
                        media["description"],
                        media["media_type"],
                        psycopg2.extras.Json(media.get("metadata", {}))
                    )
                )
                conn.commit()
                return media_id
            except psycopg2.Error as e:
                conn.rollback()
                raise
            finally:
                cursor.close()
                self._put_connection(conn)
        
        return self._retry_on_failure(_insert)
    
    def get_media_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieve media items by their IDs.
        
        Args:
            ids: List of UUID strings
        
        Returns:
            List of media item dictionaries with all fields
        
        Raises:
            psycopg2.Error: If database operation fails
        """
        if not ids:
            return []
        
        def _get():
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            try:
                # Cast string IDs to UUID type
                cursor.execute(
                    """
                    SELECT id, title, description, media_type, metadata, 
                           created_at, updated_at
                    FROM media_items
                    WHERE id = ANY(%s::uuid[])
                    """,
                    (ids,)
                )
                results = cursor.fetchall()
                return [dict(row) for row in results]
            finally:
                cursor.close()
                self._put_connection(conn)
        
        return self._retry_on_failure(_get)
    
    def get_all_media(self) -> List[Dict[str, Any]]:
        """
        Retrieve all media items from the database.
        
        Returns:
            List of media item dictionaries with all fields
        
        Raises:
            psycopg2.Error: If database operation fails
        """
        def _get():
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            try:
                cursor.execute(
                    """
                    SELECT id, title, description, media_type, metadata, 
                           created_at, updated_at
                    FROM media_items
                    ORDER BY created_at DESC
                    """
                )
                results = cursor.fetchall()
                return [dict(row) for row in results]
            finally:
                cursor.close()
                self._put_connection(conn)
        
        return self._retry_on_failure(_get)
    
    def update_media(self, id: str, updates: Dict[str, Any]) -> None:
        """
        Update an existing media item.
        
        Args:
            id: UUID string of the media item
            updates: Dictionary of fields to update
        
        Raises:
            ValueError: If no valid update fields provided
            psycopg2.Error: If database operation fails
        """
        allowed_fields = ["title", "description", "media_type", "metadata"]
        update_fields = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not update_fields:
            raise ValueError("No valid update fields provided")
        
        def _update():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                # Build dynamic UPDATE query
                set_clause = sql.SQL(", ").join(
                    sql.SQL("{} = %s").format(sql.Identifier(field))
                    for field in update_fields.keys()
                )
                
                query = sql.SQL("UPDATE media_items SET {} WHERE id = %s").format(set_clause)
                
                # Convert metadata to JSON if present
                values = list(update_fields.values())
                if "metadata" in update_fields:
                    idx = list(update_fields.keys()).index("metadata")
                    values[idx] = psycopg2.extras.Json(values[idx])
                
                values.append(id)
                
                cursor.execute(query, values)
                conn.commit()
            except psycopg2.Error as e:
                conn.rollback()
                raise
            finally:
                cursor.close()
                self._put_connection(conn)
        
        self._retry_on_failure(_update)
    
    def search_metadata(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search media items by metadata filters.
        
        Args:
            filters: Dictionary of filter criteria:
                - media_type: Filter by media type
                - genre: Filter by genre (in metadata)
                - min_year: Minimum year (in metadata)
                - max_year: Maximum year (in metadata)
                - min_rating: Minimum rating (in metadata)
        
        Returns:
            List of matching media item dictionaries
        
        Raises:
            psycopg2.Error: If database operation fails
        """
        def _search():
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            try:
                conditions = []
                params = []
                
                # Filter by media_type
                if "media_type" in filters:
                    conditions.append("media_type = %s")
                    params.append(filters["media_type"])
                
                # Filter by genre (JSONB query)
                if "genre" in filters:
                    conditions.append("metadata->>'genre' = %s")
                    params.append(filters["genre"])
                
                # Filter by year range (JSONB query)
                if "min_year" in filters:
                    conditions.append("(metadata->>'year')::int >= %s")
                    params.append(filters["min_year"])
                
                if "max_year" in filters:
                    conditions.append("(metadata->>'year')::int <= %s")
                    params.append(filters["max_year"])
                
                # Filter by minimum rating (JSONB query)
                if "min_rating" in filters:
                    conditions.append("(metadata->>'rating')::float >= %s")
                    params.append(filters["min_rating"])
                
                # Build query
                where_clause = " AND ".join(conditions) if conditions else "TRUE"
                query = f"""
                    SELECT id, title, description, media_type, metadata,
                           created_at, updated_at
                    FROM media_items
                    WHERE {where_clause}
                """
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
            finally:
                cursor.close()
                self._put_connection(conn)
        
        return self._retry_on_failure(_search)
    
    def batch_insert_media(self, media_items: List[Dict[str, Any]]) -> List[str]:
        """
        Insert multiple media items in a single transaction.
        
        Args:
            media_items: List of media item dictionaries
        
        Returns:
            List of inserted media IDs
        
        Raises:
            ValueError: If any item has invalid fields
            psycopg2.Error: If database operation fails
        """
        if not media_items:
            return []
        
        # Validate all items first
        for media in media_items:
            if not media.get("title"):
                raise ValueError("All items must have title")
            if not media.get("description"):
                raise ValueError("All items must have description")
            if media.get("media_type") not in ["book", "tv_show"]:
                raise ValueError("media_type must be 'book' or 'tv_show'")
        
        # Generate UUIDs for items without IDs
        for media in media_items:
            if "id" not in media:
                media["id"] = str(uuid.uuid4())
        
        def _batch_insert():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                # Prepare batch insert data
                insert_data = [
                    (
                        media["id"],
                        media["title"],
                        media["description"],
                        media["media_type"],
                        psycopg2.extras.Json(media.get("metadata", {}))
                    )
                    for media in media_items
                ]
                
                execute_batch(
                    cursor,
                    """
                    INSERT INTO media_items (id, title, description, media_type, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    insert_data
                )
                
                conn.commit()
                return [media["id"] for media in media_items]
            except psycopg2.Error as e:
                conn.rollback()
                raise
            finally:
                cursor.close()
                self._put_connection(conn)
        
        return self._retry_on_failure(_batch_insert)
    
    def delete_media(self, id: str) -> None:
        """
        Delete a media item by ID.
        
        Args:
            id: UUID string of the media item
        
        Raises:
            psycopg2.Error: If database operation fails
        """
        def _delete():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("DELETE FROM media_items WHERE id = %s", (id,))
                conn.commit()
            except psycopg2.Error as e:
                conn.rollback()
                raise
            finally:
                cursor.close()
                self._put_connection(conn)
        
        self._retry_on_failure(_delete)
    
    def count_media(self, media_type: Optional[str] = None) -> int:
        """
        Count total media items, optionally filtered by type.
        
        Args:
            media_type: Optional filter by 'book' or 'tv_show'
        
        Returns:
            int: Count of media items
        
        Raises:
            psycopg2.Error: If database operation fails
        """
        def _count():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                if media_type:
                    cursor.execute(
                        "SELECT COUNT(*) FROM media_items WHERE media_type = %s",
                        (media_type,)
                    )
                else:
                    cursor.execute("SELECT COUNT(*) FROM media_items")
                
                return cursor.fetchone()[0]
            finally:
                cursor.close()
                self._put_connection(conn)
        
        return self._retry_on_failure(_count)

    def get_all_media(self) -> List[Dict[str, Any]]:
        """
        Retrieve all media items from the database.

        Returns:
            List of all media item dictionaries with all fields

        Raises:
            psycopg2.Error: If database operation fails
        """
        def _get_all():
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            try:
                cursor.execute(
                    """
                    SELECT id, title, description, media_type, metadata,
                           created_at, updated_at
                    FROM media_items
                    ORDER BY created_at DESC
                    """
                )
                results = cursor.fetchall()
                return [dict(row) for row in results]
            finally:
                cursor.close()
                self._put_connection(conn)

        return self._retry_on_failure(_get_all)

