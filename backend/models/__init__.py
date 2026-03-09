"""
Models package for Pydantic schemas.

This package contains all Pydantic models used for API request/response
validation and data serialization.
"""

from .schemas import (
    MediaMetadata,
    RecommendationRequest,
    MediaRecommendation,
    RecommendationResponse,
    ErrorResponse
)

__all__ = [
    'MediaMetadata',
    'RecommendationRequest',
    'MediaRecommendation',
    'RecommendationResponse',
    'ErrorResponse'
]
