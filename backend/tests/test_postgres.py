"""
Unit tests for PostgreSQL database operations.

Tests cover CRUD operations, connection pooling, and retry logic.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
import psycopg2
from psycopg2 import OperationalError, InterfaceError

from backend.database.postgres import PostgresDatabase


@pytest.fixture
def sample_media():
    """Sample media item for testing."""
    return {
        "title": "Test Book",
        "description": "A test book description",
        "media_type": "book",
        "metadata": {
            "author": "Test Author",
            "genre": "Fiction",
            "year": 2023,
            "rating": 8.5
        }
    }


@pytest.fixture
def sample_tv_show():
    """Sample TV show for testing."""
    return {
        "title": "Test Show",
        "description": "A test TV show description",
        "media_type": "tv_show",
        "metadata": {
            "director": "Test Director",
            "genre": "Drama",
            "year": 2022,
            "rating": 9.0,
            "seasons": 3
        }
    }


class TestPostgresDatabaseValidation:
    """Test input validation for database operations."""
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_insert_media_missing_title(self, mock_pool):
        """Test that insert_media raises ValueError when title is missing."""
        db = PostgresDatabase()
        media = {"description": "Test", "media_type": "book"}
        
        with pytest.raises(ValueError, match="title is required"):
            db.insert_media(media)
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_insert_media_missing_description(self, mock_pool):
        """Test that insert_media raises ValueError when description is missing."""
        db = PostgresDatabase()
        media = {"title": "Test", "media_type": "book"}
        
        with pytest.raises(ValueError, match="description is required"):
            db.insert_media(media)
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_insert_media_invalid_media_type(self, mock_pool):
        """Test that insert_media raises ValueError for invalid media_type."""
        db = PostgresDatabase()
        media = {
            "title": "Test",
            "description": "Test description",
            "media_type": "invalid"
        }
        
        with pytest.raises(ValueError, match="media_type must be 'book' or 'tv_show'"):
            db.insert_media(media)
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_update_media_no_valid_fields(self, mock_pool):
        """Test that update_media raises ValueError when no valid fields provided."""
        db = PostgresDatabase()
        
        with pytest.raises(ValueError, match="No valid update fields provided"):
            db.update_media("test-id", {"invalid_field": "value"})
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_batch_insert_missing_title(self, mock_pool):
        """Test that batch_insert_media raises ValueError when any item missing title."""
        db = PostgresDatabase()
        media_items = [
            {"title": "Valid", "description": "Test", "media_type": "book"},
            {"description": "Missing title", "media_type": "book"}
        ]
        
        with pytest.raises(ValueError, match="All items must have title"):
            db.batch_insert_media(media_items)


class TestPostgresDatabaseConnectionPooling:
    """Test connection pooling functionality."""
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_connection_pool_initialization(self, mock_pool):
        """Test that connection pool is initialized with correct parameters."""
        db = PostgresDatabase(min_connections=2, max_connections=20)
        
        mock_pool.assert_called_once()
        args, kwargs = mock_pool.call_args
        assert args[0] == 2  # min_connections
        assert args[1] == 20  # max_connections
        assert 'host' in kwargs
        assert 'database' in kwargs
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_connection_get_and_put(self, mock_pool):
        """Test that connections are properly retrieved and returned to pool."""
        mock_pool_instance = MagicMock()
        mock_pool.return_value = mock_pool_instance
        mock_conn = MagicMock()
        mock_pool_instance.getconn.return_value = mock_conn
        
        db = PostgresDatabase()
        
        # Simulate getting a connection
        conn = db._get_connection()
        assert conn == mock_conn
        mock_pool_instance.getconn.assert_called_once()
        
        # Simulate returning a connection
        db._put_connection(conn)
        mock_pool_instance.putconn.assert_called_once_with(conn)
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_close_pool(self, mock_pool):
        """Test that close() properly closes all connections in pool."""
        mock_pool_instance = MagicMock()
        mock_pool.return_value = mock_pool_instance
        
        db = PostgresDatabase()
        db.close()
        
        mock_pool_instance.closeall.assert_called_once()


class TestPostgresDatabaseRetryLogic:
    """Test retry logic for database operations."""
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.time.sleep')
    def test_retry_on_operational_error(self, mock_sleep, mock_pool):
        """Test that operations are retried on OperationalError."""
        db = PostgresDatabase()
        
        # Create a mock operation that fails twice then succeeds
        mock_operation = Mock(side_effect=[
            OperationalError("Connection lost"),
            OperationalError("Connection lost"),
            "success"
        ])
        
        result = db._retry_on_failure(mock_operation, max_retries=3, retry_delay=0.1)
        
        assert result == "success"
        assert mock_operation.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep called between retries
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.time.sleep')
    def test_retry_on_interface_error(self, mock_sleep, mock_pool):
        """Test that operations are retried on InterfaceError."""
        db = PostgresDatabase()
        
        # Create a mock operation that fails once then succeeds
        mock_operation = Mock(side_effect=[
            InterfaceError("Connection closed"),
            "success"
        ])
        
        result = db._retry_on_failure(mock_operation, max_retries=3, retry_delay=0.1)
        
        assert result == "success"
        assert mock_operation.call_count == 2
        assert mock_sleep.call_count == 1
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.time.sleep')
    def test_retry_exhausted(self, mock_sleep, mock_pool):
        """Test that exception is raised when all retries are exhausted."""
        db = PostgresDatabase()
        
        # Create a mock operation that always fails
        mock_operation = Mock(side_effect=OperationalError("Connection lost"))
        
        with pytest.raises(OperationalError):
            db._retry_on_failure(mock_operation, max_retries=3, retry_delay=0.1)
        
        assert mock_operation.call_count == 3
        assert mock_sleep.call_count == 2
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_no_retry_on_other_errors(self, mock_pool):
        """Test that non-retryable errors are not retried."""
        db = PostgresDatabase()
        
        # Create a mock operation that raises a non-retryable error
        mock_operation = Mock(side_effect=psycopg2.IntegrityError("Constraint violation"))
        
        with pytest.raises(psycopg2.IntegrityError):
            db._retry_on_failure(mock_operation, max_retries=3)
        
        # Should only be called once (no retries)
        assert mock_operation.call_count == 1
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.time.sleep')
    def test_exponential_backoff(self, mock_sleep, mock_pool):
        """Test that retry delay increases exponentially."""
        db = PostgresDatabase()
        
        mock_operation = Mock(side_effect=[
            OperationalError("Error 1"),
            OperationalError("Error 2"),
            "success"
        ])
        
        db._retry_on_failure(mock_operation, max_retries=3, retry_delay=0.5)
        
        # Check that sleep was called with increasing delays
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls[0] == 0.5  # First retry: 0.5 * 1
        assert sleep_calls[1] == 1.0  # Second retry: 0.5 * 2


class TestPostgresDatabaseEmptyInputs:
    """Test handling of empty inputs."""
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_get_media_by_ids_empty_list(self, mock_pool):
        """Test that get_media_by_ids returns empty list for empty input."""
        db = PostgresDatabase()
        result = db.get_media_by_ids([])
        assert result == []
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    def test_batch_insert_media_empty_list(self, mock_pool):
        """Test that batch_insert_media returns empty list for empty input."""
        db = PostgresDatabase()
        result = db.batch_insert_media([])
        assert result == []


class TestPostgresDatabaseUUIDGeneration:
    """Test UUID generation for media items."""
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_insert_media_generates_uuid(self, mock_put, mock_get, mock_pool):
        """Test that insert_media generates UUID when not provided."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        
        db = PostgresDatabase()
        media = {
            "title": "Test",
            "description": "Test description",
            "media_type": "book"
        }
        
        result = db.insert_media(media)
        
        # Verify UUID was generated
        assert result is not None
        assert len(result) == 36  # UUID string length
        
        # Verify it's a valid UUID
        try:
            uuid.UUID(result)
        except ValueError:
            pytest.fail("Generated ID is not a valid UUID")
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_insert_media_uses_provided_uuid(self, mock_put, mock_get, mock_pool):
        """Test that insert_media uses provided UUID."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        
        db = PostgresDatabase()
        provided_id = str(uuid.uuid4())
        media = {
            "id": provided_id,
            "title": "Test",
            "description": "Test description",
            "media_type": "book"
        }
        
        result = db.insert_media(media)
        
        # Verify provided UUID was used
        assert result == provided_id
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.execute_batch')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_batch_insert_generates_uuids(self, mock_put, mock_get, mock_execute_batch, mock_pool):
        """Test that batch_insert_media generates UUIDs for items without IDs."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        
        db = PostgresDatabase()
        media_items = [
            {"title": "Test 1", "description": "Desc 1", "media_type": "book"},
            {"title": "Test 2", "description": "Desc 2", "media_type": "tv_show"}
        ]
        
        result = db.batch_insert_media(media_items)
        
        # Verify UUIDs were generated
        assert len(result) == 2
        for media_id in result:
            assert len(media_id) == 36
            try:
                uuid.UUID(media_id)
            except ValueError:
                pytest.fail(f"Generated ID {media_id} is not a valid UUID")


class TestPostgresDatabaseCRUDOperations:
    """Test CRUD operations with valid data."""
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_insert_media_with_valid_book(self, mock_put, mock_get, mock_pool, sample_media):
        """Test inserting a valid book media item."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        
        db = PostgresDatabase()
        result = db.insert_media(sample_media)
        
        # Verify insert was called with correct parameters
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args[0]
        assert "INSERT INTO media_items" in call_args[0]
        assert sample_media["title"] in call_args[1]
        assert sample_media["description"] in call_args[1]
        assert sample_media["media_type"] in call_args[1]
        
        # Verify commit was called
        assert mock_conn.commit.called
        
        # Verify UUID was returned
        assert result is not None
        assert isinstance(result, str)
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_insert_media_with_valid_tv_show(self, mock_put, mock_get, mock_pool, sample_tv_show):
        """Test inserting a valid TV show media item."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        
        db = PostgresDatabase()
        result = db.insert_media(sample_tv_show)
        
        # Verify insert was called
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args[0]
        assert "INSERT INTO media_items" in call_args[0]
        assert sample_tv_show["media_type"] == "tv_show"
        
        # Verify commit was called
        assert mock_conn.commit.called
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_get_media_by_ids_returns_results(self, mock_put, mock_get, mock_pool):
        """Test retrieving media items by IDs."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        
        # Mock fetchall to return sample data
        mock_cursor.fetchall.return_value = [
            {
                "id": "test-id-1",
                "title": "Test Book",
                "description": "Test description",
                "media_type": "book",
                "metadata": {"author": "Test Author"},
                "created_at": "2023-01-01",
                "updated_at": "2023-01-01"
            }
        ]
        
        db = PostgresDatabase()
        result = db.get_media_by_ids(["test-id-1"])
        
        # Verify query was executed
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args[0]
        assert "SELECT" in call_args[0]
        assert "FROM media_items" in call_args[0]
        assert "WHERE id = ANY" in call_args[0]
        
        # Verify results
        assert len(result) == 1
        assert result[0]["id"] == "test-id-1"
        assert result[0]["title"] == "Test Book"
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_get_media_by_ids_multiple_items(self, mock_put, mock_get, mock_pool):
        """Test retrieving multiple media items by IDs."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        
        # Mock fetchall to return multiple items
        mock_cursor.fetchall.return_value = [
            {"id": "id-1", "title": "Item 1", "description": "Desc 1", "media_type": "book", "metadata": {}, "created_at": "2023-01-01", "updated_at": "2023-01-01"},
            {"id": "id-2", "title": "Item 2", "description": "Desc 2", "media_type": "tv_show", "metadata": {}, "created_at": "2023-01-01", "updated_at": "2023-01-01"}
        ]
        
        db = PostgresDatabase()
        result = db.get_media_by_ids(["id-1", "id-2"])
        
        # Verify results
        assert len(result) == 2
        assert result[0]["id"] == "id-1"
        assert result[1]["id"] == "id-2"
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_update_media_title(self, mock_put, mock_get, mock_pool):
        """Test updating media title."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        
        db = PostgresDatabase()
        db.update_media("test-id", {"title": "Updated Title"})
        
        # Verify update was called
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args[0]
        # The query is a Composed object, so we check the string representation
        query_str = str(call_args[0])
        assert "UPDATE media_items" in query_str
        assert "title" in query_str
        
        # Verify commit was called
        assert mock_conn.commit.called
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_update_media_metadata(self, mock_put, mock_get, mock_pool):
        """Test updating media metadata."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        
        db = PostgresDatabase()
        new_metadata = {"author": "New Author", "year": 2024}
        db.update_media("test-id", {"metadata": new_metadata})
        
        # Verify update was called
        assert mock_cursor.execute.called
        assert mock_conn.commit.called
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_delete_media(self, mock_put, mock_get, mock_pool):
        """Test deleting a media item."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        
        db = PostgresDatabase()
        db.delete_media("test-id")
        
        # Verify delete was called
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args[0]
        assert "DELETE FROM media_items" in call_args[0]
        assert "WHERE id = %s" in call_args[0]
        assert call_args[1] == ("test-id",)
        
        # Verify commit was called
        assert mock_conn.commit.called


class TestPostgresDatabaseSearchOperations:
    """Test search and filter operations."""
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_search_metadata_by_media_type(self, mock_put, mock_get, mock_pool):
        """Test searching by media type."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        
        # Mock fetchall to return filtered results
        mock_cursor.fetchall.return_value = [
            {"id": "id-1", "title": "Book 1", "description": "Desc", "media_type": "book", "metadata": {}, "created_at": "2023-01-01", "updated_at": "2023-01-01"}
        ]
        
        db = PostgresDatabase()
        result = db.search_metadata({"media_type": "book"})
        
        # Verify query was executed with filter
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args[0]
        assert "media_type = %s" in call_args[0]
        assert "book" in call_args[1]
        
        # Verify results
        assert len(result) == 1
        assert result[0]["media_type"] == "book"
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_search_metadata_by_genre(self, mock_put, mock_get, mock_pool):
        """Test searching by genre."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        mock_cursor.fetchall.return_value = []
        
        db = PostgresDatabase()
        db.search_metadata({"genre": "Fiction"})
        
        # Verify query includes genre filter
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args[0]
        assert "metadata->>'genre'" in call_args[0]
        assert "Fiction" in call_args[1]
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_search_metadata_by_year_range(self, mock_put, mock_get, mock_pool):
        """Test searching by year range."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        mock_cursor.fetchall.return_value = []
        
        db = PostgresDatabase()
        db.search_metadata({"min_year": 2020, "max_year": 2023})
        
        # Verify query includes year filters
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args[0]
        assert "metadata->>'year'" in call_args[0]
        assert 2020 in call_args[1]
        assert 2023 in call_args[1]
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_search_metadata_by_min_rating(self, mock_put, mock_get, mock_pool):
        """Test searching by minimum rating."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        mock_cursor.fetchall.return_value = []
        
        db = PostgresDatabase()
        db.search_metadata({"min_rating": 8.0})
        
        # Verify query includes rating filter
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args[0]
        assert "metadata->>'rating'" in call_args[0]
        assert 8.0 in call_args[1]
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_search_metadata_multiple_filters(self, mock_put, mock_get, mock_pool):
        """Test searching with multiple filters combined."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        mock_cursor.fetchall.return_value = []
        
        db = PostgresDatabase()
        db.search_metadata({
            "media_type": "book",
            "genre": "Fiction",
            "min_year": 2020,
            "min_rating": 7.5
        })
        
        # Verify query includes all filters
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args[0]
        assert "media_type = %s" in call_args[0]
        assert "metadata->>'genre'" in call_args[0]
        assert "metadata->>'year'" in call_args[0]
        assert "metadata->>'rating'" in call_args[0]
        assert " AND " in call_args[0]
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_count_media_all(self, mock_put, mock_get, mock_pool):
        """Test counting all media items."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        mock_cursor.fetchone.return_value = (42,)
        
        db = PostgresDatabase()
        result = db.count_media()
        
        # Verify count query was executed
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args[0]
        assert "SELECT COUNT(*)" in call_args[0]
        assert "FROM media_items" in call_args[0]
        
        # Verify result
        assert result == 42
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_count_media_by_type(self, mock_put, mock_get, mock_pool):
        """Test counting media items by type."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        mock_cursor.fetchone.return_value = (15,)
        
        db = PostgresDatabase()
        result = db.count_media(media_type="book")
        
        # Verify count query includes filter
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args[0]
        assert "WHERE media_type = %s" in call_args[0]
        assert call_args[1] == ("book",)
        
        # Verify result
        assert result == 15


class TestPostgresDatabaseBatchOperations:
    """Test batch operations."""
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.execute_batch')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_batch_insert_multiple_items(self, mock_put, mock_get, mock_execute_batch, mock_pool):
        """Test batch inserting multiple items."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        
        db = PostgresDatabase()
        media_items = [
            {"title": "Book 1", "description": "Desc 1", "media_type": "book"},
            {"title": "Book 2", "description": "Desc 2", "media_type": "book"},
            {"title": "Show 1", "description": "Desc 3", "media_type": "tv_show"}
        ]
        
        result = db.batch_insert_media(media_items)
        
        # Verify execute_batch was called
        assert mock_execute_batch.called
        call_args = mock_execute_batch.call_args[0]
        assert "INSERT INTO media_items" in call_args[1]
        assert len(call_args[2]) == 3  # 3 items in batch
        
        # Verify commit was called
        assert mock_conn.commit.called
        
        # Verify IDs were returned
        assert len(result) == 3
        for media_id in result:
            assert isinstance(media_id, str)
            uuid.UUID(media_id)  # Verify valid UUID
    
    @patch('backend.database.postgres.psycopg2.pool.ThreadedConnectionPool')
    @patch('backend.database.postgres.execute_batch')
    @patch('backend.database.postgres.PostgresDatabase._get_connection')
    @patch('backend.database.postgres.PostgresDatabase._put_connection')
    def test_batch_insert_with_metadata(self, mock_put, mock_get, mock_execute_batch, mock_pool):
        """Test batch inserting items with metadata."""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn
        
        db = PostgresDatabase()
        media_items = [
            {
                "title": "Book 1",
                "description": "Desc 1",
                "media_type": "book",
                "metadata": {"author": "Author 1", "year": 2023}
            },
            {
                "title": "Book 2",
                "description": "Desc 2",
                "media_type": "book",
                "metadata": {"author": "Author 2", "year": 2024}
            }
        ]
        
        result = db.batch_insert_media(media_items)
        
        # Verify execute_batch was called with metadata
        assert mock_execute_batch.called
        assert mock_conn.commit.called
        assert len(result) == 2
