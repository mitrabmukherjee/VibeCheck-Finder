"""
Tests for the /recommend endpoint.

This module tests the recommendation endpoint including:
- Successful recommendation flow
- Input validation
- Error handling
- Filtering functionality
- Performance monitoring
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from backend.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_ml_engine():
    """Create a mock ML Engine."""
    mock = Mock()
    mock.vectorize_query.return_value = np.array([[0.1, 0.2, 0.3, 0.4, 0.5]])
    return mock


@pytest.fixture
def mock_vector_db():
    """Create a mock Vector Database."""
    mock = Mock()
    mock.search.return_value = [
        {"id": "id1", "score": 0.95, "metadata": {}},
        {"id": "id2", "score": 0.85, "metadata": {}},
        {"id": "id3", "score": 0.75, "metadata": {}},
    ]
    return mock


@pytest.fixture
def mock_postgres_db():
    """Create a mock PostgreSQL Database."""
    mock = Mock()
    mock.get_media_by_ids.return_value = [
        {
            "id": "id1",
            "title": "Mystery Novel",
            "description": "A thrilling mystery",
            "media_type": "book",
            "metadata": {"author": "John Doe", "genre": "mystery", "year": 2020, "rating": 8.5}
        },
        {
            "id": "id2",
            "title": "Sci-Fi Show",
            "description": "A futuristic adventure",
            "media_type": "tv_show",
            "metadata": {"director": "Jane Smith", "genre": "sci-fi", "year": 2021, "rating": 9.0}
        },
        {
            "id": "id3",
            "title": "Romance Book",
            "description": "A heartwarming story",
            "media_type": "book",
            "metadata": {"author": "Alice Brown", "genre": "romance", "year": 2019, "rating": 7.5}
        },
    ]
    return mock


@pytest.fixture
def setup_mocks(mock_ml_engine, mock_vector_db, mock_postgres_db):
    """Set up all mocks for the endpoint."""
    with patch('backend.main.ml_engine', mock_ml_engine), \
         patch('backend.main.vector_db', mock_vector_db), \
         patch('backend.main.postgres_db', mock_postgres_db):
        yield {
            'ml_engine': mock_ml_engine,
            'vector_db': mock_vector_db,
            'postgres_db': mock_postgres_db
        }


class TestRecommendEndpointSuccess:
    """Test successful recommendation flows."""
    
    def test_basic_recommendation(self, client, setup_mocks):
        """
        Test basic recommendation request with valid query.
        
        Requirements:
            - 1.1: Accept query via HTTP POST
            - 1.4: Forward valid query to ML_Engine
            - 5.1: Return JSON response with results array
            - 5.2: Include query_time_ms
        """
        response = client.post(
            "/recommend",
            json={"query": "mystery detective novel", "top_k": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "results" in data
        assert "query_time_ms" in data
        assert isinstance(data["results"], list)
        assert isinstance(data["query_time_ms"], (int, float))
        assert data["query_time_ms"] >= 0
        
        # Check results
        assert len(data["results"]) == 3
        
        # Verify ML engine was called
        setup_mocks['ml_engine'].vectorize_query.assert_called_once_with("mystery detective novel")
    
    def test_recommendation_with_default_top_k(self, client, setup_mocks):
        """Test recommendation with default top_k value."""
        response = client.post(
            "/recommend",
            json={"query": "sci-fi adventure"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        
        # Verify vector_db.search was called with default top_k=5
        setup_mocks['vector_db'].search.assert_called_once()
        call_kwargs = setup_mocks['vector_db'].search.call_args[1]
        assert call_kwargs['top_k'] == 5
    
    def test_recommendation_result_structure(self, client, setup_mocks):
        """
        Test that each recommendation has correct structure.
        
        Requirements:
            - 5.3: Include id, title, description, metadata, similarity_score
            - 4.2: Return title, description, media_type, and metadata fields
        """
        response = client.post(
            "/recommend",
            json={"query": "mystery novel", "top_k": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check first result structure
        result = data["results"][0]
        assert "id" in result
        assert "title" in result
        assert "description" in result
        assert "media_type" in result
        assert "metadata" in result
        assert "similarity_score" in result
        
        # Check metadata structure
        metadata = result["metadata"]
        assert isinstance(metadata, dict)
    
    def test_results_sorted_by_score(self, client, setup_mocks):
        """
        Test that results are sorted by similarity_score descending.
        
        Requirements:
            - 5.4: Ensure results are sorted by similarity_score descending
        """
        response = client.post(
            "/recommend",
            json={"query": "mystery novel", "top_k": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        results = data["results"]
        
        # Verify descending order
        for i in range(len(results) - 1):
            assert results[i]["similarity_score"] >= results[i + 1]["similarity_score"]
    
    def test_empty_results(self, client, setup_mocks):
        """
        Test handling of empty search results.
        
        Requirements:
            - 5.5: Return empty results array with 200 status when no results found
        """
        # Mock empty search results
        setup_mocks['vector_db'].search.return_value = []
        
        response = client.post(
            "/recommend",
            json={"query": "nonexistent query", "top_k": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert "query_time_ms" in data


class TestRecommendEndpointValidation:
    """Test input validation."""
    
    def test_empty_query_rejected(self, client, setup_mocks):
        """
        Test that empty query is rejected.
        
        Requirements:
            - 1.2: Validate query is non-empty
            - 1.3: Return error response with descriptive message
        """
        response = client.post(
            "/recommend",
            json={"query": "", "top_k": 5}
        )
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        
        # Verify ErrorResponse format
        assert "error" in data
        assert "message" in data
        assert "status_code" in data
        assert data["status_code"] == 422
    
    def test_whitespace_only_query_rejected(self, client, setup_mocks):
        """Test that whitespace-only query is rejected."""
        response = client.post(
            "/recommend",
            json={"query": "   ", "top_k": 5}
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # Verify ErrorResponse format
        assert "error" in data
        assert "message" in data
        assert "status_code" in data
    
    def test_query_too_long_rejected(self, client, setup_mocks):
        """
        Test that query longer than 1000 characters is rejected.
        
        Requirements:
            - 1.2: Validate query contains 1000 or fewer characters
            - 12.1: Reject queries longer than 1000 characters
        """
        long_query = "a" * 1001
        response = client.post(
            "/recommend",
            json={"query": long_query, "top_k": 5}
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # Verify ErrorResponse format
        assert "error" in data
        assert "message" in data
        assert "status_code" in data
        assert data["status_code"] == 422
    
    def test_top_k_below_minimum_rejected(self, client, setup_mocks):
        """
        Test that top_k < 1 is rejected.
        
        Requirements:
            - 12.2: Reject top_k values less than 1
        """
        response = client.post(
            "/recommend",
            json={"query": "mystery novel", "top_k": 0}
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # Verify ErrorResponse format
        assert "error" in data
        assert "message" in data
        assert "status_code" in data
    
    def test_top_k_above_maximum_rejected(self, client, setup_mocks):
        """
        Test that top_k > 50 is rejected.
        
        Requirements:
            - 12.2: Reject top_k values greater than 50
        """
        response = client.post(
            "/recommend",
            json={"query": "mystery novel", "top_k": 51}
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # Verify ErrorResponse format
        assert "error" in data
        assert "message" in data
        assert "status_code" in data
    
    def test_invalid_filter_media_type(self, client, setup_mocks):
        """Test that invalid media_type filter is rejected."""
        response = client.post(
            "/recommend",
            json={
                "query": "mystery novel",
                "top_k": 5,
                "filters": {"media_type": "invalid"}
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # Verify ErrorResponse format
        assert "error" in data
        assert "message" in data
        assert "status_code" in data
        assert "media_type" in data["message"].lower() or "invalid" in data["message"].lower()


class TestRecommendEndpointFiltering:
    """Test filtering functionality."""
    
    def test_filter_by_media_type(self, client, setup_mocks):
        """
        Test filtering by media_type.
        
        Requirements:
            - 15.2: Return only items matching media_type filter
        """
        response = client.post(
            "/recommend",
            json={
                "query": "mystery story",
                "top_k": 5,
                "filters": {"media_type": "book"}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all results are books
        for result in data["results"]:
            assert result["media_type"] == "book"
    
    def test_filter_by_genre(self, client, setup_mocks):
        """
        Test filtering by genre.
        
        Requirements:
            - 15.3: Return only items matching genre filter
        """
        response = client.post(
            "/recommend",
            json={
                "query": "story",
                "top_k": 5,
                "filters": {"genre": "mystery"}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all results have mystery genre
        for result in data["results"]:
            assert result["metadata"]["genre"] == "mystery"
    
    def test_filter_by_year_range(self, client, setup_mocks):
        """
        Test filtering by year range.
        
        Requirements:
            - 15.4: Return only items within year range
        """
        response = client.post(
            "/recommend",
            json={
                "query": "story",
                "top_k": 5,
                "filters": {"min_year": 2020, "max_year": 2021}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all results are within year range
        for result in data["results"]:
            year = result["metadata"]["year"]
            assert 2020 <= year <= 2021
    
    def test_filter_by_min_rating(self, client, setup_mocks):
        """
        Test filtering by minimum rating.
        
        Requirements:
            - 15.5: Return only items with rating >= min_rating
        """
        response = client.post(
            "/recommend",
            json={
                "query": "story",
                "top_k": 5,
                "filters": {"min_rating": 8.0}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all results have rating >= 8.0
        for result in data["results"]:
            assert result["metadata"]["rating"] >= 8.0
    
    def test_filter_by_is_latest(self, client, setup_mocks):
        """
        Test filtering by is_latest flag.
        
        Requirements:
            - 15.1: Apply filters to recommendation results
        """
        # Update mock to include is_latest field
        setup_mocks['postgres_db'].get_media_by_ids.return_value = [
            {
                "id": "id1",
                "title": "Latest Mystery",
                "description": "A new mystery",
                "media_type": "book",
                "metadata": {"author": "John Doe", "genre": "mystery", "year": 2024, "rating": 8.5, "is_latest": True}
            },
            {
                "id": "id2",
                "title": "Old Sci-Fi",
                "description": "A classic sci-fi",
                "media_type": "tv_show",
                "metadata": {"director": "Jane Smith", "genre": "sci-fi", "year": 2010, "rating": 9.0, "is_latest": False}
            },
        ]
        
        response = client.post(
            "/recommend",
            json={
                "query": "story",
                "top_k": 5,
                "filters": {"is_latest": True}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all results have is_latest=True
        for result in data["results"]:
            assert result["metadata"].get("is_latest", False) is True
    
    def test_filter_combination(self, client, setup_mocks):
        """
        Test filtering with multiple filters combined.
        
        Requirements:
            - 15.1: Apply filters to recommendation results
        """
        response = client.post(
            "/recommend",
            json={
                "query": "story",
                "top_k": 5,
                "filters": {
                    "media_type": "book",
                    "min_year": 2020,
                    "min_rating": 8.0
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all results match all filters
        for result in data["results"]:
            assert result["media_type"] == "book"
            assert result["metadata"]["year"] >= 2020
            assert result["metadata"]["rating"] >= 8.0
    
    def test_filtered_results_maintain_score_ordering(self, client, setup_mocks):
        """
        Test that filtered results maintain score ordering.
        
        Requirements:
            - 15.1: Ensure filtered results maintain score ordering
            - 5.4: Results sorted by similarity_score descending
        """
        response = client.post(
            "/recommend",
            json={
                "query": "story",
                "top_k": 5,
                "filters": {"media_type": "book"}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        results = data["results"]
        
        # Verify results are sorted by score descending
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]["similarity_score"] >= results[i + 1]["similarity_score"]
    
    def test_filter_excludes_items_with_missing_metadata(self, client, setup_mocks):
        """
        Test that items without required metadata fields are excluded when filtering.
        
        Requirements:
            - 15.4: Return only items within year range (excludes items with no year)
        """
        # Update mock to include items with and without year metadata
        setup_mocks['postgres_db'].get_media_by_ids.return_value = [
            {
                "id": "id1",
                "title": "Mystery Novel",
                "description": "A thrilling mystery",
                "media_type": "book",
                "metadata": {"author": "John Doe", "genre": "mystery", "year": 2020, "rating": 8.5}
            },
            {
                "id": "id2",
                "title": "Old Book",
                "description": "A classic book",
                "media_type": "book",
                "metadata": {"author": "Jane Smith", "genre": "mystery"}  # No year field
            },
        ]
        
        response = client.post(
            "/recommend",
            json={
                "query": "mystery",
                "top_k": 5,
                "filters": {"min_year": 2020}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Only id1 should be returned (has year >= 2020)
        # id2 should be excluded (no year field)
        assert len(data["results"]) == 1
        assert data["results"][0]["id"] == "id1"


class TestRecommendEndpointErrorHandling:
    """Test error handling."""
    
    def test_ml_engine_unavailable(self, client):
        """
        Test handling when ML Engine is unavailable.
        
        Requirements:
            - 13.3: Return appropriate HTTP status code
            - 13.4: Return 503 when service unavailable
        """
        with patch('backend.main.ml_engine', None):
            response = client.post(
                "/recommend",
                json={"query": "mystery novel", "top_k": 5}
            )
            
            assert response.status_code == 503
            data = response.json()
            
            # Verify ErrorResponse format
            assert "error" in data
            assert "message" in data
            assert "status_code" in data
            assert data["status_code"] == 503
    
    def test_postgres_unavailable(self, client, mock_ml_engine, mock_vector_db):
        """
        Test handling when PostgreSQL is unavailable.
        
        Requirements:
            - 13.5: Return 503 when PostgreSQL unavailable
        """
        with patch('backend.main.ml_engine', mock_ml_engine), \
             patch('backend.main.vector_db', mock_vector_db), \
             patch('backend.main.postgres_db', None):
            response = client.post(
                "/recommend",
                json={"query": "mystery novel", "top_k": 5}
            )
            
            assert response.status_code == 503
            data = response.json()
            
            # Verify ErrorResponse format
            assert "error" in data
            assert "message" in data
            assert "status_code" in data
    
    def test_vector_db_unavailable(self, client, mock_ml_engine):
        """
        Test handling when Vector DB is unavailable.
        
        Requirements:
            - 13.4: Return 503 when Vector DB unavailable
        """
        with patch('backend.main.ml_engine', mock_ml_engine), \
             patch('backend.main.vector_db', None):
            response = client.post(
                "/recommend",
                json={"query": "mystery novel", "top_k": 5}
            )
            
            assert response.status_code == 503
            data = response.json()
            
            # Verify ErrorResponse format
            assert "error" in data
            assert "message" in data
            assert "status_code" in data
    
    def test_vectorization_error(self, client, mock_ml_engine, mock_vector_db, mock_postgres_db):
        """Test handling of vectorization errors."""
        # Mock vectorization failure
        mock_ml_engine.vectorize_query.side_effect = ValueError("Query became empty after preprocessing")
        
        with patch('backend.main.ml_engine', mock_ml_engine), \
             patch('backend.main.vector_db', mock_vector_db), \
             patch('backend.main.postgres_db', mock_postgres_db):
            response = client.post(
                "/recommend",
                json={"query": "!!!", "top_k": 5}
            )
            
            assert response.status_code == 400
            data = response.json()
            
            # Verify ErrorResponse format
            assert "error" in data
            assert "message" in data
            assert "status_code" in data
    
    def test_vector_db_search_error(self, client, mock_ml_engine, mock_vector_db, mock_postgres_db):
        """Test handling of vector database search errors."""
        # Mock search failure
        mock_vector_db.search.side_effect = Exception("Connection failed")
        
        with patch('backend.main.ml_engine', mock_ml_engine), \
             patch('backend.main.vector_db', mock_vector_db), \
             patch('backend.main.postgres_db', mock_postgres_db):
            response = client.post(
                "/recommend",
                json={"query": "mystery novel", "top_k": 5}
            )
            
            assert response.status_code == 503
            data = response.json()
            
            # Verify ErrorResponse format
            assert "error" in data
            assert "message" in data
            assert "status_code" in data
    
    def test_postgres_query_error(self, client, mock_ml_engine, mock_vector_db, mock_postgres_db):
        """Test handling of PostgreSQL query errors."""
        # Mock database failure
        mock_postgres_db.get_media_by_ids.side_effect = Exception("Connection failed")
        
        with patch('backend.main.ml_engine', mock_ml_engine), \
             patch('backend.main.vector_db', mock_vector_db), \
             patch('backend.main.postgres_db', mock_postgres_db):
            response = client.post(
                "/recommend",
                json={"query": "mystery novel", "top_k": 5}
            )
            
            assert response.status_code == 503
            data = response.json()
            
            # Verify ErrorResponse format
            assert "error" in data
            assert "message" in data
            assert "status_code" in data


class TestRecommendEndpointPerformance:
    """Test performance monitoring."""
    
    def test_query_time_measured(self, client, setup_mocks):
        """
        Test that query processing time is measured and returned.
        
        Requirements:
            - 16.1: Measure total processing time
            - 16.2: Include query_time_ms in response
        """
        response = client.post(
            "/recommend",
            json={"query": "mystery novel", "top_k": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "query_time_ms" in data
        assert isinstance(data["query_time_ms"], (int, float))
        assert data["query_time_ms"] > 0  # Should take some time
        assert data["query_time_ms"] < 10000  # Should be reasonably fast (< 10 seconds)
    
    def test_query_time_included_in_empty_results(self, client, setup_mocks):
        """
        Test that query_time_ms is included even when no results are found.
        
        Requirements:
            - 16.2: Include query_time_ms in response
        """
        # Mock empty search results
        setup_mocks['vector_db'].search.return_value = []
        
        response = client.post(
            "/recommend",
            json={"query": "nonexistent query", "top_k": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "query_time_ms" in data
        assert isinstance(data["query_time_ms"], (int, float))
        assert data["query_time_ms"] >= 0
    
    def test_request_logging(self, client, setup_mocks, caplog):
        """
        Test that all requests are logged with required information.
        
        Requirements:
            - 16.3: Log request metrics
            - 16.4: Include timestamp, query length, and processing time
            - 16.5: Log all requests to /recommend endpoint
        """
        import logging
        
        with caplog.at_level(logging.INFO):
            response = client.post(
                "/recommend",
                json={"query": "mystery novel", "top_k": 5}
            )
        
        assert response.status_code == 200
        
        # Check that request was logged
        log_messages = [record.message for record in caplog.records if record.levelname == "INFO"]
        
        # Find the request log
        request_logs = [msg for msg in log_messages if "[REQUEST]" in msg]
        assert len(request_logs) > 0, "Request should be logged"
        
        request_log = request_logs[0]
        # Verify required fields in request log
        assert "timestamp=" in request_log
        assert "query_length=" in request_log
        assert "top_k=" in request_log
        
        # Find the response log
        response_logs = [msg for msg in log_messages if "[RESPONSE]" in msg]
        assert len(response_logs) > 0, "Response should be logged"
        
        response_log = response_logs[0]
        # Verify required fields in response log
        assert "timestamp=" in response_log
        assert "query_length=" in response_log
        assert "results_count=" in response_log
        assert "query_time_ms=" in response_log
    
    def test_error_logging(self, client, mock_ml_engine, mock_vector_db, mock_postgres_db, caplog):
        """
        Test that errors are logged appropriately.
        
        Requirements:
            - 13.2: Log error details
        """
        import logging
        
        # Mock vectorization failure
        mock_ml_engine.vectorize_query.side_effect = ValueError("Invalid query")
        
        with caplog.at_level(logging.WARNING):
            with patch('backend.main.ml_engine', mock_ml_engine), \
                 patch('backend.main.vector_db', mock_vector_db), \
                 patch('backend.main.postgres_db', mock_postgres_db):
                response = client.post(
                    "/recommend",
                    json={"query": "!!!", "top_k": 5}
                )
        
        assert response.status_code == 400
        
        # Check that error was logged
        log_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
        assert any("Query vectorization failed" in msg for msg in log_messages)
    
    def test_performance_monitoring_with_filters(self, client, setup_mocks):
        """
        Test that performance monitoring works correctly with filters.
        
        Requirements:
            - 16.1: Measure total processing time
            - 16.2: Include query_time_ms in response
        """
        response = client.post(
            "/recommend",
            json={
                "query": "mystery novel",
                "top_k": 5,
                "filters": {"media_type": "book", "min_rating": 8.0}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "query_time_ms" in data
        assert isinstance(data["query_time_ms"], (int, float))
        assert data["query_time_ms"] > 0


class TestRecommendEndpointDataConsistency:
    """Test data consistency."""
    
    def test_missing_metadata_handled(self, client, mock_ml_engine, mock_vector_db, mock_postgres_db):
        """
        Test handling when metadata is missing for a media ID.
        
        Requirements:
            - 4.5: Handle missing media ID gracefully and log it
            - 17.4: Verify all returned media IDs have metadata
        """
        # Mock vector_db to return an ID that doesn't have metadata
        mock_vector_db.search.return_value = [
            {"id": "id1", "score": 0.95, "metadata": {}},
            {"id": "missing_id", "score": 0.85, "metadata": {}},
        ]
        
        # Mock postgres to only return metadata for id1
        mock_postgres_db.get_media_by_ids.return_value = [
            {
                "id": "id1",
                "title": "Mystery Novel",
                "description": "A thrilling mystery",
                "media_type": "book",
                "metadata": {"author": "John Doe"}
            }
        ]
        
        with patch('backend.main.ml_engine', mock_ml_engine), \
             patch('backend.main.vector_db', mock_vector_db), \
             patch('backend.main.postgres_db', mock_postgres_db):
            response = client.post(
                "/recommend",
                json={"query": "mystery novel", "top_k": 5}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should only return results with metadata
            assert len(data["results"]) == 1
            assert data["results"][0]["id"] == "id1"


class TestErrorResponseFormat:
    """Test that all errors follow the ErrorResponse format."""
    
    def test_validation_error_format(self, client, setup_mocks):
        """
        Test that validation errors follow ErrorResponse format.
        
        Requirements:
            - 12.5: Return descriptive error message when validation fails
        """
        response = client.post(
            "/recommend",
            json={"query": "", "top_k": 5}
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # Verify ErrorResponse structure
        assert "error" in data
        assert "message" in data
        assert "status_code" in data
        assert data["status_code"] == 422
        assert isinstance(data["error"], (str, int))
        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0
    
    def test_service_unavailable_error_format(self, client):
        """
        Test that service unavailable errors follow ErrorResponse format.
        
        Requirements:
            - 13.4: Return 503 when Vector_DB unavailable
            - 13.5: Return 503 when PostgreSQL unavailable
        """
        with patch('backend.main.ml_engine', None):
            response = client.post(
                "/recommend",
                json={"query": "mystery novel", "top_k": 5}
            )
            
            assert response.status_code == 503
            data = response.json()
            
            # Verify ErrorResponse structure
            assert "error" in data
            assert "message" in data
            assert "status_code" in data
            assert data["status_code"] == 503
            assert isinstance(data["message"], str)
            assert len(data["message"]) > 0
    
    def test_bad_request_error_format(self, client, mock_ml_engine, mock_vector_db, mock_postgres_db):
        """
        Test that bad request errors follow ErrorResponse format.
        
        Requirements:
            - 1.3: Return error response with descriptive message
        """
        # Mock vectorization failure
        mock_ml_engine.vectorize_query.side_effect = ValueError("Invalid query")
        
        with patch('backend.main.ml_engine', mock_ml_engine), \
             patch('backend.main.vector_db', mock_vector_db), \
             patch('backend.main.postgres_db', mock_postgres_db):
            response = client.post(
                "/recommend",
                json={"query": "!!!", "top_k": 5}
            )
            
            assert response.status_code == 400
            data = response.json()
            
            # Verify ErrorResponse structure
            assert "error" in data
            assert "message" in data
            assert "status_code" in data
            assert data["status_code"] == 400
            assert isinstance(data["message"], str)
            assert "Invalid query" in data["message"]


class TestCORSConfiguration:
    """Test CORS middleware configuration."""
    
    def test_cors_headers_present_in_response(self, client, setup_mocks):
        """
        Test that CORS headers are present in responses.
        
        Requirements:
            - 14.1: Configure CORS middleware
            - 14.4: Include CORS headers in cross-origin responses
        """
        response = client.post(
            "/recommend",
            json={"query": "mystery novel", "top_k": 5},
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        
        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    
    def test_cors_allows_post_method(self, client, setup_mocks):
        """
        Test that POST method is allowed via CORS.
        
        Requirements:
            - 14.5: Allow POST requests to /recommend endpoint
        """
        response = client.post(
            "/recommend",
            json={"query": "mystery novel", "top_k": 5},
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        # If POST wasn't allowed, we'd get a CORS error
    
    def test_cors_preflight_request(self, client):
        """
        Test that preflight OPTIONS requests are handled correctly.
        
        Requirements:
            - 14.3: Handle preflight requests correctly
        """
        response = client.options(
            "/recommend",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # Preflight should return 200
        assert response.status_code == 200
        
        # Check for CORS preflight headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
    
    def test_cors_allows_content_type_header(self, client, setup_mocks):
        """
        Test that Content-Type header is allowed.
        
        Requirements:
            - 14.1: Configure allowed headers
        """
        response = client.post(
            "/recommend",
            json={"query": "mystery novel", "top_k": 5},
            headers={
                "Origin": "http://localhost:3000",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 200
    
    def test_cors_allows_authorization_header(self, client, setup_mocks):
        """
        Test that Authorization header is allowed.
        
        Requirements:
            - 14.1: Configure allowed headers
        """
        response = client.post(
            "/recommend",
            json={"query": "mystery novel", "top_k": 5},
            headers={
                "Origin": "http://localhost:3000",
                "Authorization": "Bearer test-token"
            }
        )
        
        # Should not fail due to Authorization header
        # (may fail for other reasons like invalid token, but not CORS)
        assert response.status_code in [200, 401, 403]
    
    def test_cors_allows_credentials(self, client, setup_mocks):
        """
        Test that credentials are allowed.
        
        Requirements:
            - 14.1: Configure CORS to allow credentials
        """
        response = client.post(
            "/recommend",
            json={"query": "mystery novel", "top_k": 5},
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        
        # Check for allow-credentials header
        assert "access-control-allow-credentials" in response.headers
        assert response.headers["access-control-allow-credentials"] == "true"



# Property-Based Tests
from hypothesis import given, strategies as st, settings, HealthCheck


class TestRecommendEndpointProperties:
    """Property-based tests for the /recommend endpoint."""
    
    @given(
        query=st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_valid_response_structure(self, client, setup_mocks, query, top_k):
        """
        Property: All valid requests return proper response structure.
        
        For any valid query and top_k, the response should:
        - Have status code 200
        - Contain 'results' and 'query_time_ms' fields
        - Have results as a list
        - Have query_time_ms as a non-negative number
        
        **Validates: Requirements 5.1, 5.2**
        """
        response = client.post(
            "/recommend",
            json={"query": query, "top_k": top_k}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert "query_time_ms" in data
        assert isinstance(data["results"], list)
        assert isinstance(data["query_time_ms"], (int, float))
        assert data["query_time_ms"] >= 0
    
    @given(
        query=st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_results_sorted_descending(self, client, setup_mocks, query, top_k):
        """
        Property: Results are always sorted by similarity_score in descending order.
        
        For any valid query and top_k, if results are returned, they must be
        sorted by similarity_score from highest to lowest.
        
        **Validates: Requirements 5.4, 3.4**
        """
        response = client.post(
            "/recommend",
            json={"query": query, "top_k": top_k}
        )
        
        assert response.status_code == 200
        data = response.json()
        results = data["results"]
        
        # If there are results, verify they are sorted
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]["similarity_score"] >= results[i + 1]["similarity_score"], \
                    f"Results not sorted: {results[i]['similarity_score']} < {results[i + 1]['similarity_score']}"
    
    @given(
        query=st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_similarity_scores_in_range(self, client, setup_mocks, query, top_k):
        """
        Property: All similarity scores are in the range [0.0, 1.0].
        
        For any valid query and top_k, all returned similarity scores must be
        between 0.0 and 1.0 inclusive (for cosine similarity).
        
        **Validates: Requirements 3.3**
        """
        response = client.post(
            "/recommend",
            json={"query": query, "top_k": top_k}
        )
        
        assert response.status_code == 200
        data = response.json()
        results = data["results"]
        
        for result in results:
            score = result["similarity_score"]
            assert 0.0 <= score <= 1.0, \
                f"Similarity score {score} is outside valid range [0.0, 1.0]"
    
    @given(
        query=st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_result_count_respects_top_k(self, client, setup_mocks, query, top_k):
        """
        Property: Number of results never exceeds top_k.
        
        For any valid query and top_k, the number of returned results should be
        at most top_k (may be less if fewer matches exist or after filtering).
        
        **Validates: Requirements 3.4, 3.5**
        """
        response = client.post(
            "/recommend",
            json={"query": query, "top_k": top_k}
        )
        
        assert response.status_code == 200
        data = response.json()
        results = data["results"]
        
        assert len(results) <= top_k, \
            f"Returned {len(results)} results, but top_k was {top_k}"
    
    @given(
        query=st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_no_duplicate_ids(self, client, setup_mocks, query, top_k):
        """
        Property: No duplicate media IDs in results.
        
        For any valid query and top_k, all returned media IDs should be unique.
        
        **Validates: Requirements 20.1, 20.4**
        """
        response = client.post(
            "/recommend",
            json={"query": query, "top_k": top_k}
        )
        
        assert response.status_code == 200
        data = response.json()
        results = data["results"]
        
        # Extract all IDs
        ids = [result["id"] for result in results]
        
        # Check for uniqueness
        assert len(ids) == len(set(ids)), \
            f"Duplicate IDs found in results: {ids}"
    
    @given(
        query=st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_all_results_have_required_fields(self, client, setup_mocks, query, top_k):
        """
        Property: All results have required fields.
        
        For any valid query and top_k, every result must contain:
        id, title, description, media_type, metadata, similarity_score
        
        **Validates: Requirements 5.3, 4.2**
        """
        response = client.post(
            "/recommend",
            json={"query": query, "top_k": top_k}
        )
        
        assert response.status_code == 200
        data = response.json()
        results = data["results"]
        
        required_fields = ["id", "title", "description", "media_type", "metadata", "similarity_score"]
        
        for result in results:
            for field in required_fields:
                assert field in result, \
                    f"Result missing required field '{field}': {result}"


class TestRecommendEndpointFilteringProperties:
    """Property-based tests for filtering functionality."""
    
    @given(
        query=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=10),
        media_type=st.sampled_from(["book", "tv_show"])
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_media_type_filter_consistency(self, client, setup_mocks, query, top_k, media_type):
        """
        Property: When media_type filter is applied, all results match that type.
        
        For any valid query, top_k, and media_type filter, all returned results
        must have the specified media_type.
        
        **Validates: Requirements 15.2**
        """
        response = client.post(
            "/recommend",
            json={
                "query": query,
                "top_k": top_k,
                "filters": {"media_type": media_type}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        results = data["results"]
        
        # All results must match the filter
        for result in results:
            assert result["media_type"] == media_type, \
                f"Result has media_type '{result['media_type']}' but filter was '{media_type}'"
    
    @given(
        query=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=10),
        min_rating=st.floats(min_value=0.0, max_value=10.0)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_min_rating_filter_consistency(self, client, setup_mocks, query, top_k, min_rating):
        """
        Property: When min_rating filter is applied, all results have rating >= min_rating.
        
        For any valid query, top_k, and min_rating filter, all returned results
        must have a rating greater than or equal to min_rating.
        
        **Validates: Requirements 15.5**
        """
        response = client.post(
            "/recommend",
            json={
                "query": query,
                "top_k": top_k,
                "filters": {"min_rating": min_rating}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        results = data["results"]
        
        # All results must have rating >= min_rating
        for result in results:
            rating = result["metadata"].get("rating")
            if rating is not None:
                assert rating >= min_rating, \
                    f"Result has rating {rating} but min_rating filter was {min_rating}"
    
    @given(
        query=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=10),
        min_year=st.integers(min_value=1800, max_value=2024),
        max_year=st.integers(min_value=1800, max_value=2026)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_year_range_filter_consistency(self, client, setup_mocks, query, top_k, min_year, max_year):
        """
        Property: When year range filters are applied, all results fall within range.
        
        For any valid query, top_k, and year range filters, all returned results
        must have a year within the specified range.
        
        **Validates: Requirements 15.4**
        """
        # Skip if min_year > max_year (invalid range)
        if min_year > max_year:
            return
        
        response = client.post(
            "/recommend",
            json={
                "query": query,
                "top_k": top_k,
                "filters": {"min_year": min_year, "max_year": max_year}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        results = data["results"]
        
        # All results must have year within range
        for result in results:
            year = result["metadata"].get("year")
            if year is not None:
                assert min_year <= year <= max_year, \
                    f"Result has year {year} but range was [{min_year}, {max_year}]"
    
    @given(
        query=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=10),
        genre=st.sampled_from(["mystery", "sci-fi", "romance"])
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_genre_filter_consistency(self, client, setup_mocks, query, top_k, genre):
        """
        Property: When genre filter is applied, all results match that genre.
        
        For any valid query, top_k, and genre filter, all returned results
        must have the specified genre.
        
        **Validates: Requirements 15.3**
        """
        response = client.post(
            "/recommend",
            json={
                "query": query,
                "top_k": top_k,
                "filters": {"genre": genre}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        results = data["results"]
        
        # All results must match the genre filter
        for result in results:
            result_genre = result["metadata"].get("genre")
            assert result_genre == genre, \
                f"Result has genre '{result_genre}' but filter was '{genre}'"
    
    @given(
        query=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_filtered_results_maintain_ordering(self, client, setup_mocks, query, top_k):
        """
        Property: Filtered results maintain score ordering.
        
        For any valid query, top_k, and filters, the returned results must be
        sorted by similarity_score in descending order.
        
        **Validates: Requirements 15.1, 5.4**
        """
        # Test with a random filter
        filters = {"media_type": "book"}
        
        response = client.post(
            "/recommend",
            json={
                "query": query,
                "top_k": top_k,
                "filters": filters
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        results = data["results"]
        
        # Verify results are sorted by score descending
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]["similarity_score"] >= results[i + 1]["similarity_score"], \
                    f"Filtered results not sorted: {results[i]['similarity_score']} < {results[i + 1]['similarity_score']}"


class TestRecommendEndpointPerformanceProperties:
    """Property-based tests for performance monitoring."""
    
    @given(
        query=st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_query_time_always_present(self, client, setup_mocks, query, top_k):
        """
        Property: query_time_ms is always present in response.
        
        For any valid query and top_k, the response must include query_time_ms.
        
        **Validates: Requirements 16.2**
        """
        response = client.post(
            "/recommend",
            json={"query": query, "top_k": top_k}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "query_time_ms" in data, "query_time_ms must be present in response"
        assert isinstance(data["query_time_ms"], (int, float)), \
            "query_time_ms must be a number"
    
    @given(
        query=st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_query_time_non_negative(self, client, setup_mocks, query, top_k):
        """
        Property: query_time_ms is always non-negative.
        
        For any valid query and top_k, the query_time_ms must be >= 0.
        
        **Validates: Requirements 16.1, 16.2**
        """
        response = client.post(
            "/recommend",
            json={"query": query, "top_k": top_k}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["query_time_ms"] >= 0, \
            f"query_time_ms must be non-negative, got {data['query_time_ms']}"
    
    @given(
        query=st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_query_time_reasonable(self, client, setup_mocks, query, top_k):
        """
        Property: query_time_ms is within reasonable bounds.
        
        For any valid query and top_k, the query_time_ms should be reasonable
        (not negative, not excessively large).
        
        **Validates: Requirements 16.1**
        """
        response = client.post(
            "/recommend",
            json={"query": query, "top_k": top_k}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be positive (takes some time)
        assert data["query_time_ms"] >= 0
        
        # Should be reasonable (< 60 seconds for a simple query)
        assert data["query_time_ms"] < 60000, \
            f"query_time_ms seems too large: {data['query_time_ms']}ms"
    
    @given(
        query=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=10),
        media_type=st.sampled_from(["book", "tv_show"])
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_query_time_with_filters(self, client, setup_mocks, query, top_k, media_type):
        """
        Property: query_time_ms is present even with filters applied.
        
        For any valid query, top_k, and filters, the response must include
        query_time_ms.
        
        **Validates: Requirements 16.1, 16.2**
        """
        response = client.post(
            "/recommend",
            json={
                "query": query,
                "top_k": top_k,
                "filters": {"media_type": media_type}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "query_time_ms" in data
        assert isinstance(data["query_time_ms"], (int, float))
        assert data["query_time_ms"] >= 0
    
    @given(
        query=st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_query_time_precision(self, client, setup_mocks, query, top_k):
        """
        Property: query_time_ms has reasonable precision.
        
        For any valid query and top_k, the query_time_ms should be a finite
        number with reasonable precision (not NaN, not Infinity).
        
        **Validates: Requirements 16.1, 16.2**
        """
        response = client.post(
            "/recommend",
            json={"query": query, "top_k": top_k}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        import math
        query_time = data["query_time_ms"]
        
        # Must be finite (not NaN or Infinity)
        assert math.isfinite(query_time), \
            f"query_time_ms must be finite, got {query_time}"
        
        # Must be a real number
        assert isinstance(query_time, (int, float)), \
            f"query_time_ms must be a number, got {type(query_time)}"


