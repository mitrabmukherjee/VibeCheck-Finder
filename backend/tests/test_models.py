"""
Unit and property-based tests for Pydantic models.

This module tests the validation logic for all Pydantic models used in
the FastAPI backend, including request/response models and metadata.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from hypothesis import given, strategies as st, assume, settings

from backend.models import (
    MediaMetadata,
    RecommendationRequest,
    MediaRecommendation,
    RecommendationResponse,
    ErrorResponse
)


# ============================================================================
# Unit Tests for MediaMetadata
# ============================================================================

class TestMediaMetadata:
    """Unit tests for MediaMetadata model validation."""
    
    def test_valid_metadata_all_fields(self):
        """Test creating metadata with all valid fields."""
        metadata = MediaMetadata(
            author="Jane Doe",
            genre="Mystery",
            year=2020,
            rating=8.5,
            director="John Smith",
            seasons=3,
            is_latest=True,
            thumbnail_url="https://example.com/image.jpg"
        )
        assert metadata.author == "Jane Doe"
        assert metadata.genre == "Mystery"
        assert metadata.year == 2020
        assert metadata.rating == 8.5
        assert metadata.director == "John Smith"
        assert metadata.seasons == 3
        assert metadata.is_latest is True
        assert metadata.thumbnail_url == "https://example.com/image.jpg"
    
    def test_valid_metadata_minimal(self):
        """Test creating metadata with no optional fields."""
        metadata = MediaMetadata()
        assert metadata.author is None
        assert metadata.genre is None
        assert metadata.year is None
        assert metadata.rating is None
        assert metadata.is_latest is False
    
    def test_year_validation_too_early(self):
        """Test year validation rejects years before 1800."""
        with pytest.raises(ValidationError) as exc_info:
            MediaMetadata(year=1799)
        assert "year must be 1800 or later" in str(exc_info.value)
    
    def test_year_validation_too_late(self):
        """Test year validation rejects years more than 2 years in future."""
        future_year = datetime.now().year + 3
        with pytest.raises(ValidationError) as exc_info:
            MediaMetadata(year=future_year)
        assert "cannot be more than 2 years in the future" in str(exc_info.value)
    
    def test_year_validation_boundary_valid(self):
        """Test year validation accepts boundary values."""
        current_year = datetime.now().year
        
        # Test minimum valid year
        metadata_min = MediaMetadata(year=1800)
        assert metadata_min.year == 1800
        
        # Test maximum valid year
        metadata_max = MediaMetadata(year=current_year + 2)
        assert metadata_max.year == current_year + 2
    
    def test_rating_validation_too_low(self):
        """Test rating validation rejects values below 0."""
        with pytest.raises(ValidationError) as exc_info:
            MediaMetadata(rating=-0.1)
        assert "rating must be between 0 and 10" in str(exc_info.value)
    
    def test_rating_validation_too_high(self):
        """Test rating validation rejects values above 10."""
        with pytest.raises(ValidationError) as exc_info:
            MediaMetadata(rating=10.1)
        assert "rating must be between 0 and 10" in str(exc_info.value)
    
    def test_rating_validation_boundary_valid(self):
        """Test rating validation accepts boundary values."""
        metadata_min = MediaMetadata(rating=0.0)
        assert metadata_min.rating == 0.0
        
        metadata_max = MediaMetadata(rating=10.0)
        assert metadata_max.rating == 10.0
    
    def test_seasons_validation_invalid(self):
        """Test seasons validation rejects values less than 1."""
        with pytest.raises(ValidationError) as exc_info:
            MediaMetadata(seasons=0)
        assert "seasons must be at least 1" in str(exc_info.value)


# ============================================================================
# Unit Tests for RecommendationRequest
# ============================================================================

class TestRecommendationRequest:
    """Unit tests for RecommendationRequest model validation."""
    
    def test_valid_request_minimal(self):
        """Test creating request with only required fields."""
        request = RecommendationRequest(query="mystery novel")
        assert request.query == "mystery novel"
        assert request.top_k == 5  # Default value
        assert request.filters is None
    
    def test_valid_request_all_fields(self):
        """Test creating request with all fields."""
        request = RecommendationRequest(
            query="sci-fi adventure",
            top_k=10,
            filters={"media_type": "book", "genre": "Science Fiction"}
        )
        assert request.query == "sci-fi adventure"
        assert request.top_k == 10
        assert request.filters == {"media_type": "book", "genre": "Science Fiction"}
    
    def test_query_validation_empty_string(self):
        """Test query validation rejects empty strings."""
        with pytest.raises(ValidationError) as exc_info:
            RecommendationRequest(query="")
        assert "String should have at least 1 character" in str(exc_info.value)
    
    def test_query_validation_whitespace_only(self):
        """Test query validation rejects whitespace-only strings."""
        with pytest.raises(ValidationError) as exc_info:
            RecommendationRequest(query="   ")
        assert "query must contain non-whitespace characters" in str(exc_info.value)
    
    def test_query_validation_too_long(self):
        """Test query validation rejects strings longer than 1000 characters."""
        long_query = "a" * 1001
        with pytest.raises(ValidationError) as exc_info:
            RecommendationRequest(query=long_query)
        assert "String should have at most 1000 characters" in str(exc_info.value)
    
    def test_query_validation_boundary_valid(self):
        """Test query validation accepts boundary values."""
        # Test maximum valid length
        max_query = "a" * 1000
        request = RecommendationRequest(query=max_query)
        assert len(request.query) == 1000
    
    def test_top_k_validation_too_low(self):
        """Test top_k validation rejects values less than 1."""
        with pytest.raises(ValidationError) as exc_info:
            RecommendationRequest(query="test", top_k=0)
        assert "greater than or equal to 1" in str(exc_info.value)
    
    def test_top_k_validation_too_high(self):
        """Test top_k validation rejects values greater than 50."""
        with pytest.raises(ValidationError) as exc_info:
            RecommendationRequest(query="test", top_k=51)
        assert "less than or equal to 50" in str(exc_info.value)
    
    def test_top_k_validation_boundary_valid(self):
        """Test top_k validation accepts boundary values."""
        request_min = RecommendationRequest(query="test", top_k=1)
        assert request_min.top_k == 1
        
        request_max = RecommendationRequest(query="test", top_k=50)
        assert request_max.top_k == 50
    
    def test_filters_validation_invalid_media_type(self):
        """Test filters validation rejects invalid media_type."""
        with pytest.raises(ValidationError) as exc_info:
            RecommendationRequest(
                query="test",
                filters={"media_type": "movie"}
            )
        assert "media_type filter must be 'book' or 'tv_show'" in str(exc_info.value)
    
    def test_filters_validation_invalid_year_range(self):
        """Test filters validation rejects invalid year ranges."""
        with pytest.raises(ValidationError) as exc_info:
            RecommendationRequest(
                query="test",
                filters={"min_year": 2020, "max_year": 2010}
            )
        assert "min_year cannot be greater than max_year" in str(exc_info.value)
    
    def test_filters_validation_year_too_early(self):
        """Test filters validation rejects years before 1800."""
        with pytest.raises(ValidationError) as exc_info:
            RecommendationRequest(
                query="test",
                filters={"min_year": 1799}
            )
        assert "min_year must be 1800 or later" in str(exc_info.value)
    
    def test_filters_validation_year_too_late(self):
        """Test filters validation rejects years too far in future."""
        future_year = datetime.now().year + 3
        with pytest.raises(ValidationError) as exc_info:
            RecommendationRequest(
                query="test",
                filters={"max_year": future_year}
            )
        assert "cannot be more than 2 years in the future" in str(exc_info.value)
    
    def test_filters_validation_invalid_rating(self):
        """Test filters validation rejects invalid ratings."""
        with pytest.raises(ValidationError) as exc_info:
            RecommendationRequest(
                query="test",
                filters={"min_rating": 11}
            )
        assert "min_rating must be between 0 and 10" in str(exc_info.value)
    
    def test_filters_validation_empty_genre(self):
        """Test filters validation rejects empty genre strings."""
        with pytest.raises(ValidationError) as exc_info:
            RecommendationRequest(
                query="test",
                filters={"genre": "   "}
            )
        assert "genre cannot be empty" in str(exc_info.value)
    
    def test_filters_validation_valid_all_filters(self):
        """Test filters validation accepts all valid filter combinations."""
        current_year = datetime.now().year
        request = RecommendationRequest(
            query="test",
            filters={
                "media_type": "book",
                "genre": "Mystery",
                "min_year": 2000,
                "max_year": current_year,
                "min_rating": 7.5,
                "is_latest": True
            }
        )
        assert request.filters["media_type"] == "book"
        assert request.filters["genre"] == "Mystery"
        assert request.filters["min_year"] == 2000
        assert request.filters["max_year"] == current_year
        assert request.filters["min_rating"] == 7.5
        assert request.filters["is_latest"] is True


# ============================================================================
# Unit Tests for MediaRecommendation
# ============================================================================

class TestMediaRecommendation:
    """Unit tests for MediaRecommendation model validation."""
    
    def test_valid_recommendation(self):
        """Test creating valid recommendation."""
        recommendation = MediaRecommendation(
            id="123e4567-e89b-12d3-a456-426614174000",
            title="The Mystery Novel",
            description="A thrilling mystery story",
            media_type="book",
            metadata=MediaMetadata(author="Jane Doe", genre="Mystery"),
            similarity_score=0.85
        )
        assert recommendation.id == "123e4567-e89b-12d3-a456-426614174000"
        assert recommendation.title == "The Mystery Novel"
        assert recommendation.similarity_score == 0.85
    
    def test_title_validation_empty(self):
        """Test title validation rejects empty strings."""
        with pytest.raises(ValidationError) as exc_info:
            MediaRecommendation(
                id="test-id",
                title="",
                description="Test description",
                media_type="book",
                metadata=MediaMetadata(),
                similarity_score=0.5
            )
        assert "String should have at least 1 character" in str(exc_info.value)
    
    def test_title_validation_too_long(self):
        """Test title validation rejects strings longer than 500 characters."""
        long_title = "a" * 501
        with pytest.raises(ValidationError) as exc_info:
            MediaRecommendation(
                id="test-id",
                title=long_title,
                description="Test description",
                media_type="book",
                metadata=MediaMetadata(),
                similarity_score=0.5
            )
        assert "String should have at most 500 characters" in str(exc_info.value)
    
    def test_description_validation_too_long(self):
        """Test description validation rejects strings longer than 5000 characters."""
        long_desc = "a" * 5001
        with pytest.raises(ValidationError) as exc_info:
            MediaRecommendation(
                id="test-id",
                title="Test Title",
                description=long_desc,
                media_type="book",
                metadata=MediaMetadata(),
                similarity_score=0.5
            )
        assert "String should have at most 5000 characters" in str(exc_info.value)
    
    def test_media_type_validation_invalid(self):
        """Test media_type validation rejects invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            MediaRecommendation(
                id="test-id",
                title="Test Title",
                description="Test description",
                media_type="movie",
                metadata=MediaMetadata(),
                similarity_score=0.5
            )
        assert "media_type must be 'book' or 'tv_show'" in str(exc_info.value)
    
    def test_similarity_score_validation_too_low(self):
        """Test similarity_score validation rejects values below 0."""
        with pytest.raises(ValidationError) as exc_info:
            MediaRecommendation(
                id="test-id",
                title="Test Title",
                description="Test description",
                media_type="book",
                metadata=MediaMetadata(),
                similarity_score=-0.1
            )
        assert "greater than or equal to 0" in str(exc_info.value)
    
    def test_similarity_score_validation_too_high(self):
        """Test similarity_score validation rejects values above 1."""
        with pytest.raises(ValidationError) as exc_info:
            MediaRecommendation(
                id="test-id",
                title="Test Title",
                description="Test description",
                media_type="book",
                metadata=MediaMetadata(),
                similarity_score=1.1
            )
        assert "less than or equal to 1" in str(exc_info.value)
    
    def test_similarity_score_validation_boundary_valid(self):
        """Test similarity_score validation accepts boundary values."""
        rec_min = MediaRecommendation(
            id="test-id",
            title="Test Title",
            description="Test description",
            media_type="book",
            metadata=MediaMetadata(),
            similarity_score=0.0
        )
        assert rec_min.similarity_score == 0.0
        
        rec_max = MediaRecommendation(
            id="test-id",
            title="Test Title",
            description="Test description",
            media_type="book",
            metadata=MediaMetadata(),
            similarity_score=1.0
        )
        assert rec_max.similarity_score == 1.0


# ============================================================================
# Unit Tests for RecommendationResponse
# ============================================================================

class TestRecommendationResponse:
    """Unit tests for RecommendationResponse model validation."""
    
    def test_valid_response_with_results(self):
        """Test creating valid response with results."""
        results = [
            MediaRecommendation(
                id="id1",
                title="Title 1",
                description="Description 1",
                media_type="book",
                metadata=MediaMetadata(),
                similarity_score=0.9
            ),
            MediaRecommendation(
                id="id2",
                title="Title 2",
                description="Description 2",
                media_type="book",
                metadata=MediaMetadata(),
                similarity_score=0.8
            )
        ]
        response = RecommendationResponse(results=results, query_time_ms=123.45)
        assert len(response.results) == 2
        assert response.query_time_ms == 123.45
    
    def test_valid_response_empty_results(self):
        """Test creating valid response with empty results."""
        response = RecommendationResponse(results=[], query_time_ms=50.0)
        assert len(response.results) == 0
        assert response.query_time_ms == 50.0
    
    def test_results_sorting_validation_fails(self):
        """Test response validation fails when results are not sorted."""
        results = [
            MediaRecommendation(
                id="id1",
                title="Title 1",
                description="Description 1",
                media_type="book",
                metadata=MediaMetadata(),
                similarity_score=0.7  # Lower score first - invalid!
            ),
            MediaRecommendation(
                id="id2",
                title="Title 2",
                description="Description 2",
                media_type="book",
                metadata=MediaMetadata(),
                similarity_score=0.9  # Higher score second - invalid!
            )
        ]
        with pytest.raises(ValidationError) as exc_info:
            RecommendationResponse(results=results, query_time_ms=100.0)
        assert "Results must be sorted by similarity_score descending" in str(exc_info.value)
    
    def test_results_sorting_validation_passes(self):
        """Test response validation passes when results are properly sorted."""
        results = [
            MediaRecommendation(
                id="id1",
                title="Title 1",
                description="Description 1",
                media_type="book",
                metadata=MediaMetadata(),
                similarity_score=0.9
            ),
            MediaRecommendation(
                id="id2",
                title="Title 2",
                description="Description 2",
                media_type="book",
                metadata=MediaMetadata(),
                similarity_score=0.8
            ),
            MediaRecommendation(
                id="id3",
                title="Title 3",
                description="Description 3",
                media_type="book",
                metadata=MediaMetadata(),
                similarity_score=0.7
            )
        ]
        response = RecommendationResponse(results=results, query_time_ms=100.0)
        assert len(response.results) == 3
    
    def test_query_time_validation_negative(self):
        """Test query_time_ms validation rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            RecommendationResponse(results=[], query_time_ms=-1.0)
        assert "greater than or equal to 0" in str(exc_info.value)


# ============================================================================
# Unit Tests for ErrorResponse
# ============================================================================

class TestErrorResponse:
    """Unit tests for ErrorResponse model."""
    
    def test_valid_error_response(self):
        """Test creating valid error response."""
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid query parameter",
            status_code=400
        )
        assert error.error == "ValidationError"
        assert error.message == "Invalid query parameter"
        assert error.status_code == 400


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestPropertyBasedValidation:
    """Property-based tests for model validation using Hypothesis."""
    
    @given(
        year=st.integers(min_value=1800, max_value=datetime.now().year + 2),
        rating=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=10)
    def test_property_metadata_valid_ranges(self, year: int, rating: float):
        """
        Property: MediaMetadata accepts all values within valid ranges.
        
        **Validates: Requirements 12.3, 12.4**
        """
        metadata = MediaMetadata(year=year, rating=rating)
        assert metadata.year == year
        assert metadata.rating == rating
    
    @given(
        query=st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()),
        top_k=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=10)
    def test_property_request_valid_ranges(self, query: str, top_k: int):
        """
        Property: RecommendationRequest accepts all values within valid ranges.
        
        **Validates: Requirements 1.2, 12.1, 12.2**
        """
        request = RecommendationRequest(query=query, top_k=top_k)
        assert request.query == query
        assert request.top_k == top_k
    
    @given(
        score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=10)
    def test_property_similarity_score_valid_range(self, score: float):
        """
        Property: MediaRecommendation accepts all similarity scores in [0, 1].
        
        **Validates: Requirements 3.3**
        """
        recommendation = MediaRecommendation(
            id="test-id",
            title="Test Title",
            description="Test description",
            media_type="book",
            metadata=MediaMetadata(),
            similarity_score=score
        )
        assert 0.0 <= recommendation.similarity_score <= 1.0
    
    @given(
        scores=st.lists(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=0,
            max_size=10
        )
    )
    @settings(max_examples=10)
    def test_property_response_sorting_requirement(self, scores: list):
        """
        Property: RecommendationResponse only accepts results sorted descending.
        
        **Validates: Requirements 5.4**
        """
        # Sort scores in descending order
        sorted_scores = sorted(scores, reverse=True)
        
        # Create recommendations with sorted scores
        results = [
            MediaRecommendation(
                id=f"id{i}",
                title=f"Title {i}",
                description=f"Description {i}",
                media_type="book",
                metadata=MediaMetadata(),
                similarity_score=score
            )
            for i, score in enumerate(sorted_scores)
        ]
        
        # Should succeed with sorted scores
        response = RecommendationResponse(results=results, query_time_ms=100.0)
        assert len(response.results) == len(sorted_scores)
        
        # Verify sorting is maintained
        if len(response.results) > 1:
            for i in range(len(response.results) - 1):
                assert response.results[i].similarity_score >= response.results[i + 1].similarity_score
