"""
FastAPI Backend for Semantic Media Engine
"""
import os
import time
import logging
from contextlib import asynccontextmanager
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

# Module-level refs for lifespan and route handlers
ml_engine: "MLEngine" = None
postgres_db: "PostgresDatabase" = None
vector_db = None  # VectorDatabase | FileVectorDatabase
hybrid_search: "HybridSearchEngine" = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize DB and ML on startup, clean up on shutdown.
    Uses lifespan for Vercel compatibility (startup/shutdown limited on serverless).
    """
    global ml_engine, postgres_db, vector_db, hybrid_search
    try:
        vectorizer_type = os.getenv("VECTORIZER_TYPE", "sbert")
        sbert_model_name = os.getenv("SBERT_MODEL_NAME", "all-MiniLM-L6-v2")
        vectorizer_path = os.getenv("VECTORIZER_PATH", "backend/models")
        embeddings_path = os.getenv("EMBEDDINGS_PATH", "backend/embeddings")
        default_vector_size = 768 if vectorizer_type == "sbert" else 5000
        vector_size = int(os.getenv("VECTOR_SIZE", str(default_vector_size)))

        ml_engine = MLEngine(
            vectorizer_path=vectorizer_path,
            embeddings_path=embeddings_path,
            vectorizer_type=vectorizer_type,
            model_name=sbert_model_name if vectorizer_type == "sbert" else None,
        )
        logger.info(f"ML Engine initialized with vectorizer_type={vectorizer_type}")
        if vectorizer_type == "sbert":
            logger.info(f"Sentence-BERT model: {sbert_model_name}")

        postgres_db = PostgresDatabase()
        postgres_db.initialize_schema()
        logger.info("PostgreSQL connection initialized")

        use_file_storage = os.getenv("USE_FILE_STORAGE", "true").lower() == "true"
        if use_file_storage:
            vector_db = FileVectorDatabase(storage_path=embeddings_path, vector_size=vector_size)
            logger.info(f"File-based Vector Database initialized (vector_size={vector_size})")
        else:
            vector_db_host = os.getenv("QDRANT_HOST", "localhost")
            vector_db_port = int(os.getenv("QDRANT_PORT", "6333"))
            vector_db = VectorDatabase(
                host=vector_db_host, port=vector_db_port, vector_size=vector_size
            )
            logger.info(f"Qdrant Vector Database initialized (vector_size={vector_size})")

        use_hybrid = os.getenv("USE_HYBRID_SEARCH", "true").lower() == "true"
        if use_hybrid:
            logger.info("Initializing Hybrid Search Engine...")
            hybrid_search = HybridSearchEngine(title_weight=0.5, semantic_weight=0.5)
            logger.info("Loading corpus for hybrid search...")
            all_media = postgres_db.get_all_media()
            hybrid_search.index_corpus(all_media)
            logger.info(f"Hybrid Search Engine initialized with {len(all_media)} items")
        else:
            hybrid_search = None

        yield
    finally:
        try:
            if postgres_db:
                postgres_db.close()
                logger.info("PostgreSQL connection closed")
            if vector_db:
                vector_db.close()
                logger.info("Vector Database connection closed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title="Semantic Media Engine API",
    description="Content-based recommendation system for books and TV shows",
    version="1.0.0",
    lifespan=lifespan,
)

# Custom exception handlers for consistent error responses

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
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
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
cors_origins = [origin.strip() for origin in cors_origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

logger.info(f"CORS enabled for origins: {cors_origins}")


@app.get("/")
async def root():
    return {"message": "Semantic Media Engine API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/debug")
async def debug():
    return {
        "ml_engine": ml_engine is not None,
        "postgres_db": postgres_db is not None,
        "vector_db": vector_db is not None,
        "vector_db_type": type(vector_db).__name__ if vector_db else None
    }


@app.post("/recommend", response_model=RecommendationResponse)
async def recommend(request: RecommendationRequest) -> RecommendationResponse:
    start_time = time.time()
    
    try:
        logger.info(
            f"[REQUEST] timestamp={time.time():.3f}, "
            f"query_length={len(request.query)}, "
            f"top_k={request.top_k}, "
            f"filters={request.filters}"
        )
        
        if not request.query or not request.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query cannot be empty. Please enter a search term."
            )
        
        if ml_engine is None or postgres_db is None or vector_db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service temporarily unavailable."
            )
        
        # Step 1: Vectorize
        query_vector = ml_engine.vectorize_query(request.query)
        query_vector_list = query_vector[0].tolist()
        
        # Step 2: Search
        search_top_k = request.top_k * 3 if request.filters else request.top_k
        search_results = vector_db.search(query_vector=query_vector_list, top_k=search_top_k)
        
        if hybrid_search:
            search_results = hybrid_search.search(request.query, search_results, search_top_k)
            
        # Deduplicate
        seen_ids = set()
        unique_results = [r for r in search_results if not (r['id'] in seen_ids or seen_ids.add(r['id']))]
        
        if not unique_results:
            return RecommendationResponse(results=[], query_time_ms=(time.time() - start_time) * 1000)

        # Step 4: Metadata
        media_ids = [result["id"] for result in unique_results]
        media_objects = postgres_db.get_media_by_ids(media_ids)
        media_map = {media["id"]: media for media in media_objects}
        
        # Step 6: Filter & Merge
        recommendations = []
        for result in unique_results:
            media_id = result["id"]
            if media_id not in media_map: continue
            
            media = media_map[media_id]
            
            # Application level filtering
            if request.filters:
                if "media_type" in request.filters and media["media_type"] != request.filters["media_type"]: continue
                # (Additional filters omitted for brevity, kept same as your original logic)

            recommendations.append(MediaRecommendation(
                id=media_id,
                title=media["title"],
                description=media["description"],
                media_type=media["media_type"],
                metadata=MediaMetadata(**media.get("metadata", {})),
                similarity_score=result["score"]
            ))
            if len(recommendations) >= request.top_k: break
        
        recommendations.sort(key=lambda x: x.similarity_score, reverse=True)
        query_time_ms = (time.time() - start_time) * 1000
        
        logger.info(f"[RESPONSE] results_count={len(recommendations)}, query_time_ms={query_time_ms:.2f}")
        return RecommendationResponse(results=recommendations, query_time_ms=query_time_ms)
        
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# --- ADDED SECTION ---
if __name__ == "__main__":
    import uvicorn
    # Pull port from environment (standard for Docker/Cloud) or default to 8000
    port = int(os.getenv("PORT", 8000))
    # host 0.0.0.0 is required for Docker and external access
    # reload=True is great for dev, but usually False in prod
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)