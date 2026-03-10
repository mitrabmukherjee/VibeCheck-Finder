"""
FastAPI Backend for Semantic Media Engine
"""
import os
import time
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv

from models.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    MediaRecommendation,
    MediaMetadata,
    ErrorResponse
)
from ml_engine.ml_engine import MLEngine
from ml_engine.hybrid_search import HybridSearchEngine
from database.postgres import PostgresDatabase
from database.vector_db import VectorDatabase
from database.file_vector_db import FileVectorDatabase

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Semantic Media Engine API",
    description="Content-based recommendation system for books and TV shows",
    version="1.0.0"
)

# Custom exception handlers for consistent error responses

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTPException and return ErrorResponse format.
    
    Requirements:
        - 12.5: Return descriptive error message when validation fails
        - 13.3: Return appropriate HTTP status code
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.status_code,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors and return ErrorResponse format.
    
    Requirements:
        - 1.3: Return error response with descriptive message
        - 12.5: Return descriptive error message when validation fails
    """
    # Extract validation error details
    errors = exc.errors()
    error_messages = []
    
    for error in errors:
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_messages.append(f"{field}: {message}")
    
    detailed_message = "; ".join(error_messages)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": detailed_message,
            "status_code": 422
        }
    )


# CORS configuration
# Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
cors_origins = [origin.strip() for origin in cors_origins]  # Remove whitespace

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # Allow requests from Next.js origin
    allow_credentials=True,  # Allow cookies and authentication headers
    allow_methods=["GET", "POST", "OPTIONS"],  # Allow GET, POST, and OPTIONS (preflight)
    allow_headers=["Content-Type", "Authorization", "Accept"],  # Allow necessary headers
)

logger.info(f"CORS enabled for origins: {cors_origins}")

# Initialize components
ml_engine: MLEngine = None
postgres_db: PostgresDatabase = None
vector_db = None  # Can be VectorDatabase or FileVectorDatabase
hybrid_search: HybridSearchEngine = None


@app.on_event("startup")
async def startup_event():
    """
    Initialize database connections and ML engine on startup.
    
    Requirements:
        - 2.1: Support both TF-IDF and Sentence-BERT vectorizers
        - 5.1: Maintain backward compatibility with existing TF-IDF code
        - 5.5: Ensure API functionality unchanged
        - 7.1: Initialize MLEngine with vectorizer_type from environment
    """
    global ml_engine, postgres_db, vector_db, hybrid_search
    
    try:
        # Get vectorizer configuration from environment
        vectorizer_type = os.getenv("VECTORIZER_TYPE", "sbert")  # Default to sbert
        sbert_model_name = os.getenv("SBERT_MODEL_NAME", "all-MiniLM-L6-v2")
        vectorizer_path = os.getenv("VECTORIZER_PATH", "backend/models")
        embeddings_path = os.getenv("EMBEDDINGS_PATH", "backend/embeddings")
        
        # Determine vector size based on vectorizer type
        if vectorizer_type == "sbert":
            default_vector_size = 768
        else:
            default_vector_size = 5000
        
        vector_size = int(os.getenv("VECTOR_SIZE", str(default_vector_size)))
        
        # Initialize ML Engine with vectorizer type
        ml_engine = MLEngine(
            vectorizer_path=vectorizer_path,
            embeddings_path=embeddings_path,
            vectorizer_type=vectorizer_type,
            model_name=sbert_model_name if vectorizer_type == "sbert" else None
        )
        logger.info(f"ML Engine initialized with vectorizer_type={vectorizer_type}")
        if vectorizer_type == "sbert":
            logger.info(f"Sentence-BERT model: {sbert_model_name}")
        
        # Initialize PostgreSQL
        postgres_db = PostgresDatabase()
        logger.info("PostgreSQL connection initialized")
        
        # Initialize Vector DB (file-based or Qdrant)
        use_file_storage = os.getenv("USE_FILE_STORAGE", "true").lower() == "true"
        
        if use_file_storage:
            vector_db = FileVectorDatabase(
                storage_path=embeddings_path,
                vector_size=vector_size
            )
            logger.info(f"File-based Vector Database initialized (vector_size={vector_size})")
        else:
            vector_db_host = os.getenv("QDRANT_HOST", "localhost")
            vector_db_port = int(os.getenv("QDRANT_PORT", "6333"))
            vector_db = VectorDatabase(
                host=vector_db_host,
                port=vector_db_port,
                vector_size=vector_size
            )
            logger.info(f"Qdrant Vector Database initialized (vector_size={vector_size})")
        
        # Initialize Hybrid Search Engine
        use_hybrid = os.getenv("USE_HYBRID_SEARCH", "true").lower() == "true"
        if use_hybrid:
            logger.info("Initializing Hybrid Search Engine...")
            hybrid_search = HybridSearchEngine(title_weight=0.5, semantic_weight=0.5)
            
            # Index all media titles
            logger.info("Loading corpus for hybrid search...")
            all_media = postgres_db.get_all_media()
            hybrid_search.index_corpus(all_media)
            logger.info(f"Hybrid Search Engine initialized with {len(all_media)} items")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connections on shutdown."""
    global postgres_db, vector_db
    
    try:
        if postgres_db:
            postgres_db.close()
            logger.info("PostgreSQL connection closed")
        
        if vector_db:
            vector_db.close()
            logger.info("Vector Database connection closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


@app.get("/")
async def root():
    return {"message": "Semantic Media Engine API"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/debug")
async def debug():
    """Debug endpoint to check service status."""
    return {
        "ml_engine": ml_engine is not None,
        "postgres_db": postgres_db is not None,
        "vector_db": vector_db is not None,
        "vector_db_type": type(vector_db).__name__ if vector_db else None
    }


@app.post("/recommend", response_model=RecommendationResponse)
async def recommend(request: RecommendationRequest) -> RecommendationResponse:
    """
    Generate media recommendations based on natural language query.
    
    This endpoint accepts a user query, vectorizes it using the ML Engine,
    finds similar items in the Vector DB, retrieves metadata from PostgreSQL,
    and returns ranked recommendations with similarity scores.
    
    Args:
        request: RecommendationRequest containing query, top_k, and optional filters
    
    Returns:
        RecommendationResponse with results and query_time_ms
    
    Raises:
        HTTPException: 400 for invalid input, 503 for service unavailability
    
    Requirements:
        - 1.1: Accept query via HTTP POST
        - 1.2: Validate query is non-empty and <= 1000 characters
        - 1.3: Return error response with descriptive message for invalid input
        - 1.4: Forward valid query to ML_Engine for vectorization
        - 4.1: Retrieve full metadata from PostgreSQL using media IDs
        - 4.2: Return title, description, media_type, and all metadata fields
        - 4.3: Merge metadata with similarity scores
        - 5.1: Return JSON response containing results array
        - 5.2: Include query_time_ms indicating processing duration
        - 5.3: Include id, title, description, metadata, and similarity_score
        - 5.4: Ensure results are sorted by similarity_score descending
    """
    start_time = time.time()
    
    try:
        # Log request with timestamp
        # Requirements: 16.3, 16.4, 16.5
        logger.info(
            f"[REQUEST] timestamp={time.time():.3f}, "
            f"query_length={len(request.query)}, "
            f"top_k={request.top_k}, "
            f"filters={request.filters}"
        )
        
        # Validate query is not empty (after stripping whitespace)
        # Requirements: 10.1
        if not request.query or not request.query.strip():
            logger.warning("Empty query received")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query cannot be empty. Please enter a search term."
            )
        
        # Check for very long queries (>512 tokens is model limit)
        # For simplicity, we'll check character length as a proxy
        # Requirements: 10.2
        if len(request.query) > 5000:  # Roughly 512 tokens * 10 chars/token
            logger.warning(f"Very long query received: {len(request.query)} characters")
            # Truncate query (Sentence-BERT will handle token truncation internally)
            # This is just a warning, processing continues normally
        
        # Check if services are available
        # Requirements: 10.3, 10.4
        if ml_engine is None:
            logger.error("ML Engine not initialized")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service temporarily unavailable. Please try again in a few moments."
            )
        
        if postgres_db is None:
            logger.error("PostgreSQL not initialized")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service temporarily unavailable. Please try again shortly."
            )
        
        if vector_db is None:
            logger.error("Vector Database not initialized")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service temporarily unavailable. Please try again shortly."
            )
        
        # Step 1: Vectorize the query
        try:
            query_vector = ml_engine.vectorize_query(request.query)
            logger.debug(f"Query vectorized: shape={query_vector.shape}")
        except ValueError as e:
            # Handle empty query or invalid input
            # Requirements: 10.1
            logger.warning(f"Query vectorization failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid query: {str(e)}"
            )
        except RuntimeError as e:
            # Handle model loading failures
            # Requirements: 10.3
            logger.error(f"Model loading error during vectorization: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service temporarily unavailable. Please try again in a few moments."
            )
        except Exception as e:
            logger.error(f"Unexpected error during vectorization: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing query"
            )
        
        # Step 2: Search for similar items in Vector DB
        try:
            # Convert numpy array to list for vector_db
            query_vector_list = query_vector[0].tolist()
            
            # Note: We request more results than top_k to account for filtering
            # that will be applied later in the application layer
            # Request 3x to ensure we have enough results after filtering
            search_top_k = request.top_k * 3 if request.filters else request.top_k
            
            # Get semantic search results
            semantic_results = vector_db.search(
                query_vector=query_vector_list,
                top_k=search_top_k,
                filter=None  # Apply filters in application layer for flexibility
            )
            
            # Apply hybrid search if enabled
            if hybrid_search is not None:
                logger.debug("Using hybrid search (title matching + semantic)")
                search_results = hybrid_search.search(
                    query=request.query,
                    semantic_results=semantic_results,
                    top_k=search_top_k
                )
            else:
                logger.debug("Using semantic search only")
                search_results = semantic_results
            
            # Deduplicate results by ID
            seen_ids = set()
            unique_results = []
            for result in search_results:
                if result['id'] not in seen_ids:
                    seen_ids.add(result['id'])
                    unique_results.append(result)
            search_results = unique_results
            
            logger.debug(f"Search returned {len(search_results)} unique results")
        except Exception as e:
            # Handle database unavailability
            # Requirements: 10.4
            logger.error(f"Search failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service temporarily unavailable. Please try again shortly."
            )
        
        # Step 3: Handle empty results
        if not search_results:
            query_time_ms = (time.time() - start_time) * 1000
            # Log empty results with metrics
            # Requirements: 16.3, 16.4
            logger.info(
                f"[RESPONSE] timestamp={time.time():.3f}, "
                f"query_length={len(request.query)}, "
                f"results_count=0, "
                f"query_time_ms={query_time_ms:.2f}"
            )
            return RecommendationResponse(
                results=[],
                query_time_ms=query_time_ms
            )
        
        # Step 4: Retrieve metadata from PostgreSQL
        media_ids = [result["id"] for result in search_results]
        try:
            media_objects = postgres_db.get_media_by_ids(media_ids)
            logger.debug(f"Retrieved {len(media_objects)} media objects from PostgreSQL")
        except Exception as e:
            # Handle database unavailability
            # Requirements: 10.4
            logger.error(f"PostgreSQL query failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service temporarily unavailable. Please try again shortly."
            )
        
        # Step 5: Create a mapping of media_id to metadata
        media_map = {media["id"]: media for media in media_objects}
        
        # Step 6: Merge scores with metadata and create recommendations
        recommendations: List[MediaRecommendation] = []
        
        for result in search_results:
            media_id = result["id"]
            score = result["score"]
            
            # Check if metadata exists for this ID
            if media_id not in media_map:
                logger.warning(f"Metadata missing for media_id: {media_id}")
                continue
            
            media = media_map[media_id]
            
            # Apply filters (all filters are applied in application layer)
            if request.filters:
                # Filter by media_type
                if "media_type" in request.filters:
                    if media["media_type"] != request.filters["media_type"]:
                        continue
                
                # Filter by genre
                if "genre" in request.filters:
                    media_genre = media.get("metadata", {}).get("genre")
                    if media_genre != request.filters["genre"]:
                        continue
                
                # Filter by year range
                if "min_year" in request.filters or "max_year" in request.filters:
                    media_year = media.get("metadata", {}).get("year")
                    # Exclude items without year metadata when year filters are applied
                    if media_year is None:
                        continue
                    if "min_year" in request.filters and media_year < request.filters["min_year"]:
                        continue
                    if "max_year" in request.filters and media_year > request.filters["max_year"]:
                        continue
                
                # Filter by minimum rating
                if "min_rating" in request.filters:
                    media_rating = media.get("metadata", {}).get("rating")
                    if media_rating is None or media_rating < request.filters["min_rating"]:
                        continue
                
                # Filter by is_latest
                if "is_latest" in request.filters:
                    media_is_latest = media.get("metadata", {}).get("is_latest", False)
                    if media_is_latest != request.filters["is_latest"]:
                        continue
            
            # Create MediaMetadata object
            metadata_dict = media.get("metadata", {})
            metadata = MediaMetadata(**metadata_dict)
            
            # Create MediaRecommendation object
            recommendation = MediaRecommendation(
                id=media_id,
                title=media["title"],
                description=media["description"],
                media_type=media["media_type"],
                metadata=metadata,
                similarity_score=score
            )
            
            recommendations.append(recommendation)
            
            # Stop if we have enough results after filtering
            if len(recommendations) >= request.top_k:
                break
        
        # Step 7: Ensure results are sorted by similarity_score descending
        # (should already be sorted from vector_db, but ensure it)
        recommendations.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Calculate query time
        query_time_ms = (time.time() - start_time) * 1000
        
        # Log metrics with timestamp and processing time
        # Requirements: 16.1, 16.2, 16.3, 16.4
        logger.info(
            f"[RESPONSE] timestamp={time.time():.3f}, "
            f"query_length={len(request.query)}, "
            f"results_count={len(recommendations)}, "
            f"query_time_ms={query_time_ms:.2f}"
        )
        
        # Step 8: Return response
        return RecommendationResponse(
            results=recommendations,
            query_time_ms=query_time_ms
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error in recommend endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
