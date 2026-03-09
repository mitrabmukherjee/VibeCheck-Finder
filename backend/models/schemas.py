"""
Pydantic models for FastAPI request/response validation.

This module defines the data models used for API communication between
the frontend and backend, including request validation and response formatting.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime


class MediaMetadata(BaseModel):
    """
    Additional metadata for media items.
    
    This model represents optional metadata fields that can be associated
    with books or TV shows, such as author, genre, year, and rating.
    
    Requirements:
        - 10.3: Validate title is non-empty and at most 500 characters
        - 10.4: Validate description is non-empty and at most 5000 characters
        - 12.3: Validate year is between 1800 and current year + 2
        - 12.4: Validate rating is between 0 and 10
    """
    
    author: Optional[str] = Field(None, description="Author name (for books)")
    genre: Optional[str] = Field(None, description="Genre classification")
    year: Optional[int] = Field(None, description="Publication/release year")
    rating: Optional[float] = Field(None, description="Average rating (0-10)")
    director: Optional[str] = Field(None, description="Director name (for TV shows)")
    seasons: Optional[int] = Field(None, description="Number of seasons (for TV shows)")
    is_latest: Optional[bool] = Field(False, description="Coming soon/latest flag")
    thumbnail_url: Optional[str] = Field(None, description="Cover image URL")
    
    @field_validator('year')
    @classmethod
    def validate_year(cls, v: Optional[int]) -> Optional[int]:
        """
        Validate year is within acceptable range.
        
        Requirements:
            - 12.3: Reject years before 1800 or more than 2 years in the future
        """
        if v is not None:
            current_year = datetime.now().year
            if v < 1800:
                raise ValueError("year must be 1800 or later")
            if v > current_year + 2:
                raise ValueError(f"year cannot be more than 2 years in the future (max: {current_year + 2})")
        return v
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v: Optional[float]) -> Optional[float]:
        """
        Validate rating is within acceptable range.
        
        Requirements:
            - 12.4: Reject ratings outside the range 0 to 10
        """
        if v is not None:
            if v < 0 or v > 10:
                raise ValueError("rating must be between 0 and 10")
        return v
    
    @field_validator('seasons')
    @classmethod
    def validate_seasons(cls, v: Optional[int]) -> Optional[int]:
        """Validate seasons is a positive integer."""
        if v is not None and v < 1:
            raise ValueError("seasons must be at least 1")
        return v


class RecommendationRequest(BaseModel):
    """
    Request model for recommendation endpoint.
    
    This model validates incoming recommendation requests from the frontend,
    ensuring query text and parameters meet system requirements.
    
    Requirements:
        - 1.2: Validate query is non-empty and contains 1000 or fewer characters
        - 12.1: Reject queries longer than 1000 characters
        - 12.2: Reject top_k values less than 1 or greater than 50
    """
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User's natural language search query"
    )
    top_k: int = Field(
        5,
        ge=1,
        le=50,
        description="Number of recommendations to return (1-50)"
    )
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata filters for recommendations"
    )
    
    @field_validator('query')
    @classmethod
    def validate_query_not_empty(cls, v: str) -> str:
        """
        Validate query contains non-whitespace characters.
        
        Requirements:
            - 1.2: Validate query is non-empty
        """
        if not v.strip():
            raise ValueError("query must contain non-whitespace characters")
        return v
    
    @field_validator('filters')
    @classmethod
    def validate_filters(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Validate filter values are within acceptable ranges.
        
        Requirements:
            - 12.3: Validate year filters
            - 12.4: Validate rating filters
            - 15.1, 15.2, 15.3, 15.4, 15.5: Validate filter structure
        """
        if v is None:
            return v
        
        # Validate media_type filter
        if 'media_type' in v:
            if v['media_type'] not in ['book', 'tv_show']:
                raise ValueError("media_type filter must be 'book' or 'tv_show'")
        
        # Validate year range filters
        current_year = datetime.now().year
        if 'min_year' in v:
            if not isinstance(v['min_year'], int):
                raise ValueError("min_year must be an integer")
            if v['min_year'] < 1800:
                raise ValueError("min_year must be 1800 or later")
        
        if 'max_year' in v:
            if not isinstance(v['max_year'], int):
                raise ValueError("max_year must be an integer")
            if v['max_year'] > current_year + 2:
                raise ValueError(f"max_year cannot be more than 2 years in the future (max: {current_year + 2})")
        
        # Validate year range consistency
        if 'min_year' in v and 'max_year' in v:
            if v['min_year'] > v['max_year']:
                raise ValueError("min_year cannot be greater than max_year")
        
        # Validate rating filter
        if 'min_rating' in v:
            if not isinstance(v['min_rating'], (int, float)):
                raise ValueError("min_rating must be a number")
            if v['min_rating'] < 0 or v['min_rating'] > 10:
                raise ValueError("min_rating must be between 0 and 10")
        
        # Validate genre filter
        if 'genre' in v:
            if not isinstance(v['genre'], str):
                raise ValueError("genre must be a string")
            if not v['genre'].strip():
                raise ValueError("genre cannot be empty")
        
        # Validate is_latest filter
        if 'is_latest' in v:
            if not isinstance(v['is_latest'], bool):
                raise ValueError("is_latest must be a boolean")
        
        return v


class MediaRecommendation(BaseModel):
    """
    Single media recommendation with similarity score.
    
    This model represents a recommended media item with its metadata
    and similarity score relative to the user's query.
    
    Requirements:
        - 5.3: Include id, title, description, metadata, and similarity_score
        - 3.3: Ensure similarity_score is in range 0.0 to 1.0
    """
    
    id: str = Field(..., description="Unique media identifier (UUID)")
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Media title"
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Media description/synopsis"
    )
    media_type: str = Field(..., description="Type of media: 'book' or 'tv_show'")
    metadata: MediaMetadata = Field(..., description="Additional metadata")
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity score (0.0 to 1.0)"
    )
    
    @field_validator('media_type')
    @classmethod
    def validate_media_type(cls, v: str) -> str:
        """Validate media_type is either 'book' or 'tv_show'."""
        if v not in ['book', 'tv_show']:
            raise ValueError("media_type must be 'book' or 'tv_show'")
        return v


class RecommendationResponse(BaseModel):
    """
    Response model for recommendation endpoint.
    
    This model formats the recommendation results returned to the frontend,
    including the list of recommendations and performance metrics.
    
    Requirements:
        - 5.1: Return JSON response containing a results array
        - 5.2: Include query_time_ms indicating processing duration
        - 5.4: Ensure results are sorted by similarity_score descending
        - 5.5: Return empty results array with 200 status when no results found
    """
    
    results: List[MediaRecommendation] = Field(
        ...,
        description="List of media recommendations sorted by similarity score"
    )
    query_time_ms: float = Field(
        ...,
        ge=0.0,
        description="Query processing time in milliseconds"
    )
    
    @model_validator(mode='after')
    def validate_results_sorted(self) -> 'RecommendationResponse':
        """
        Validate that results are sorted by similarity_score in descending order.
        
        Requirements:
            - 5.4: Ensure results are sorted by similarity_score descending
        """
        if len(self.results) > 1:
            for i in range(len(self.results) - 1):
                if self.results[i].similarity_score < self.results[i + 1].similarity_score:
                    raise ValueError(
                        f"Results must be sorted by similarity_score descending. "
                        f"Found {self.results[i].similarity_score} before "
                        f"{self.results[i + 1].similarity_score} at index {i}"
                    )
        return self


class ErrorResponse(BaseModel):
    """
    Error response model for API errors.
    
    This model provides a consistent format for error messages
    returned to the frontend.
    
    Requirements:
        - 1.3: Return error response with descriptive message
        - 12.5: Return descriptive error message when validation fails
    """
    
    error: str = Field(..., description="Error type or category")
    message: str = Field(..., description="Detailed error message")
    status_code: int = Field(..., description="HTTP status code")
