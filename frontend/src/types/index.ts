/**
 * Type definitions for Semantic Media Engine
 * 
 * These interfaces match the backend Pydantic models defined in backend/models/schemas.py
 * to ensure type safety when communicating with the API.
 * 
 * Requirements: 5.3
 */

/**
 * Additional metadata for media items.
 * 
 * Represents optional metadata fields that can be associated with books or TV shows,
 * such as author, genre, year, and rating.
 */
export interface MediaMetadata {
  /** Author name (for books) */
  readonly author?: string
  /** Genre classification */
  readonly genre?: string
  /** Publication/release year (1800 to current year + 2) */
  readonly year?: number
  /** Average rating (0-10) */
  readonly rating?: number
  /** Director name (for TV shows) */
  readonly director?: string
  /** Number of seasons (for TV shows) */
  readonly seasons?: number
  /** Coming soon/latest flag */
  readonly is_latest?: boolean
  /** Cover image URL */
  readonly thumbnail_url?: string
}

/**
 * Single media recommendation with similarity score.
 * 
 * Represents a recommended media item with its metadata and similarity score
 * relative to the user's query.
 * 
 * Requirements: 5.3, 3.3
 */
export interface MediaRecommendation {
  /** Unique media identifier (UUID) */
  readonly id: string
  /** Media title (1-500 characters) */
  readonly title: string
  /** Media description/synopsis (1-5000 characters) */
  readonly description: string
  /** Type of media: 'book' or 'tv_show' */
  readonly media_type: 'book' | 'tv_show'
  /** Additional metadata */
  readonly metadata: MediaMetadata
  /** Similarity score (0.0 to 1.0) */
  readonly similarity_score: number
}

/**
 * Request model for recommendation endpoint.
 * 
 * Validates incoming recommendation requests from the frontend,
 * ensuring query text and parameters meet system requirements.
 * 
 * Requirements: 1.2, 12.1, 12.2
 */
export interface RecommendationRequest {
  /** User's natural language search query (1-1000 characters) */
  query: string
  /** Number of recommendations to return (1-50, default: 5) */
  top_k?: number
  /** Optional metadata filters for recommendations */
  filters?: {
    /** Filter by media type */
    media_type?: 'book' | 'tv_show'
    /** Filter by genre */
    genre?: string
    /** Minimum publication/release year (1800 or later) */
    min_year?: number
    /** Maximum publication/release year (current year + 2 or earlier) */
    max_year?: number
    /** Minimum rating (0-10) */
    min_rating?: number
    /** Filter for latest/coming soon items */
    is_latest?: boolean
  }
}

/**
 * Response model for recommendation endpoint.
 * 
 * Formats the recommendation results returned from the backend,
 * including the list of recommendations and performance metrics.
 * 
 * Requirements: 5.1, 5.2, 5.4, 5.5
 */
export interface RecommendationResponse {
  /** List of media recommendations sorted by similarity score (descending) */
  readonly results: readonly MediaRecommendation[]
  /** Query processing time in milliseconds */
  readonly query_time_ms: number
}

/**
 * Error response model for API errors.
 * 
 * Provides a consistent format for error messages returned from the backend.
 * 
 * Requirements: 1.3, 12.5
 */
export interface ErrorResponse {
  /** Error type or category */
  readonly error: string
  /** Detailed error message */
  readonly message: string
  /** HTTP status code */
  readonly status_code: number
}
