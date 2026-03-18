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
from ml_engine.query_parser import parse as parse_query
from database.postgres import PostgresDatabase
from database.vector_db import VectorDatabase
from database.file_vector_db import FileVectorDatabase
from database.postgres_vector_db import PostgresVectorDatabase
from api.tmdb import get_full_details, get_landing_data, get_poster_images

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

        use_postgres_vectors = os.getenv("USE_POSTGRES_VECTORS", "false").lower() == "true"
        use_file_storage = os.getenv("USE_FILE_STORAGE", "true").lower() == "true"

        if use_postgres_vectors:
            vector_db = PostgresVectorDatabase(postgres_db=postgres_db, vector_size=vector_size)
            logger.info(f"Postgres Vector Database initialized (vector_size={vector_size})")
        elif use_file_storage:
            vector_db = FileVectorDatabase(storage_path=embeddings_path, vector_size=vector_size)
            logger.info(f"File-based Vector Database initialized (vector_size={vector_size})")
        else:
            vector_db_host = os.getenv("QDRANT_HOST", "localhost")
            vector_db_port = int(os.getenv("QDRANT_PORT", "6333"))
            vector_db = VectorDatabase(
                host=vector_db_host, port=vector_db_port, vector_size=vector_size
            )
            logger.info(f"Qdrant Vector Database initialized (vector_size={vector_size})")

        if vector_db.count() == 0:
            logger.info("No embeddings found. Auto-generating from database (this may take a few minutes)...")
            all_media = postgres_db.get_all_media()
            if all_media:
                descriptions = [f"{m['title']}. {m['description']}" for m in all_media]
                media_ids = [str(m["id"]) for m in all_media]
                embeddings = ml_engine.compute_embeddings(descriptions, media_ids, batch_size=64)
                items = [
                    (media_ids[i], embeddings[i].tolist(), {})
                    for i in range(len(media_ids))
                ]
                if hasattr(vector_db, "batch_insert"):
                    vector_db.batch_insert(items)
                else:
                    for item_id, vec, meta in items:
                        vector_db.insert(item_id, vec, meta)
                logger.info(f"Auto-generated {len(all_media)} embeddings successfully")
            else:
                logger.warning("No media items in database — skipping embedding generation")

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
cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"
).split(",")
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

        # Step 1: Parse query — extract intent, media_type, year, clean text
        parsed = parse_query(request.query)
        logger.info(
            f"[PARSED] intent={parsed.intent}, media_type={parsed.media_type}, "
            f"year={parsed.year}, clean_query={parsed.clean_query!r}"
        )

        # Step 2: Embed the clean query (strips noise like "movie", "from 2019")
        # so the semantic vector reflects pure emotional/conceptual content.
        embed_text = parsed.clean_query if parsed.clean_query else request.query
        query_vector = ml_engine.vectorize_query(embed_text)
        query_vector_list = query_vector[0].tolist()

        # Step 3: Semantic vector search — fetch a wider pool for re-ranking.
        # Genre/media_type filtering is applied after vector search, so we
        # fetch a much larger candidate pool to ensure enough items survive
        # the filter (a genre may cover only ~5-15% of the corpus).
        has_filters = bool(request.filters) or parsed.media_type or parsed.year or parsed.genre
        if parsed.genre:
            search_top_k = max(request.top_k * 15, 150)
        elif has_filters:
            search_top_k = request.top_k * 5
        else:
            search_top_k = request.top_k * 2
        search_results = vector_db.search(query_vector=query_vector_list, top_k=search_top_k)

        # Step 4: Hybrid re-rank with tiered priority model
        if hybrid_search:
            search_results = hybrid_search.search(
                request.query,
                search_results,
                search_top_k,
                parsed_query=parsed,
            )

        # Deduplicate by id
        seen_ids: set = set()
        unique_results = [
            r for r in search_results
            if not (r["id"] in seen_ids or seen_ids.add(r["id"]))
        ]

        if not unique_results:
            return RecommendationResponse(results=[], query_time_ms=(time.time() - start_time) * 1000)

        # Step 5: Fetch metadata from Postgres
        media_ids = [result["id"] for result in unique_results]
        media_objects = postgres_db.get_media_by_ids(media_ids)
        media_map = {media["id"]: media for media in media_objects}

        # Step 6: Build effective filters from request + auto-extracted params.
        #
        # HARD filters  (media_type, year, rating) — items that fail are skipped.
        # SOFT filter   (genre) — items are bucketed: genre matches come first,
        #               non-genre matches fill remaining slots.  This means
        #               "documentary about politician" returns documentaries first,
        #               then other genres that semantically match "politician".
        import re as _re
        import json as _json

        def _norm_genre(s: str) -> str:
            return _re.sub(r'[-_\s]+', '', s.lower())

        def _get_meta(media: Dict[str, Any]) -> Dict[str, Any]:
            meta = media.get("metadata") or {}
            if isinstance(meta, str):
                try:
                    meta = _json.loads(meta)
                except Exception:
                    meta = {}
            return meta if isinstance(meta, dict) else {}

        effective_filters: Dict[str, Any] = dict(request.filters or {})
        if parsed.media_type and "media_type" not in effective_filters:
            effective_filters["media_type"] = parsed.media_type
        if parsed.year:
            # Use a ±1 year window so "show from 2019" also surfaces 2018/2020
            # content — exact year matches are rare and zero results is worse
            # than a near-year result.  Explicit min_year/max_year from the
            # request filters always take precedence.
            if "min_year" not in effective_filters:
                effective_filters["min_year"] = parsed.year - 1
            if "max_year" not in effective_filters:
                effective_filters["max_year"] = parsed.year + 1

        # Genre is extracted separately for soft bucketing
        genre_filter: str | None = None
        if parsed.genre and "genre" not in effective_filters:
            genre_filter = parsed.genre
        elif "genre" in effective_filters:
            genre_filter = effective_filters.pop("genre")

        def _matches_genre(media: Dict[str, Any], target_genre: str) -> bool:
            meta = _get_meta(media)
            genres = meta.get("genres") or meta.get("genre") or []
            if isinstance(genres, str):
                genres = [genres]
            norm = _norm_genre(target_genre)
            return any(norm in _norm_genre(g) or _norm_genre(g) in norm for g in genres)

        def _passes_hard_filters(media: Dict[str, Any]) -> bool:
            if not effective_filters:
                return True
            if "media_type" in effective_filters and media["media_type"] != effective_filters["media_type"]:
                return False
            meta = _get_meta(media)
            release_year = meta.get("year") or meta.get("release_year")
            if "min_year" in effective_filters and release_year:
                if int(release_year) < int(effective_filters["min_year"]):
                    return False
            if "max_year" in effective_filters and release_year:
                if int(release_year) > int(effective_filters["max_year"]):
                    return False
            if "min_rating" in effective_filters:
                rating = meta.get("rating")
                if rating is not None and float(rating) < float(effective_filters["min_rating"]):
                    return False
            return True

        # Two buckets: genre matches first, then semantically-relevant others
        genre_bucket: List[MediaRecommendation] = []
        other_bucket: List[MediaRecommendation] = []

        for result in unique_results:
            media_id = result["id"]
            if media_id not in media_map:
                continue
            media = media_map[media_id]

            if not _passes_hard_filters(media):
                continue

            rec = MediaRecommendation(
                id=media_id,
                title=media["title"],
                description=media["description"],
                media_type=media["media_type"],
                metadata=MediaMetadata(**media.get("metadata", {})),
                similarity_score=result["score"],
            )

            if genre_filter:
                if _matches_genre(media, genre_filter):
                    genre_bucket.append(rec)
                else:
                    other_bucket.append(rec)
            else:
                genre_bucket.append(rec)

        # Sort each bucket by score, then combine: genre first, others after
        genre_bucket.sort(key=lambda x: x.similarity_score, reverse=True)
        other_bucket.sort(key=lambda x: x.similarity_score, reverse=True)
        recommendations = (genre_bucket + other_bucket)[:request.top_k]
        query_time_ms = (time.time() - start_time) * 1000
        
        logger.info(f"[RESPONSE] results_count={len(recommendations)}, query_time_ms={query_time_ms:.2f}")
        return RecommendationResponse(results=recommendations, query_time_ms=query_time_ms)
        
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/media/{media_id}/details")
def media_details(media_id: str):
    """
    Return TMDB-enriched details for a single media item:
      - cast (top 10)
      - streaming providers (region-aware)
      - trailer YouTube URL
    """
    if postgres_db is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    # Fetch the media item from Postgres to get title / year / media_type
    items = postgres_db.get_media_by_ids([media_id])
    if not items:
        raise HTTPException(status_code=404, detail="Media item not found.")

    item = items[0]
    title      = item["title"]
    media_type = item["media_type"]

    # Extract year from metadata JSONB
    meta = item.get("metadata") or {}
    if isinstance(meta, str):
        import json as _json
        try:
            meta = _json.loads(meta)
        except Exception:
            meta = {}
    year = meta.get("year") or meta.get("release_year")
    year = int(year) if year else None

    try:
        details = get_full_details(title, year, media_type)
    except Exception as exc:
        logger.error(f"TMDB enrichment failed for '{title}': {exc}", exc_info=True)
        details = {
            "tmdb_id":   None,
            "cast":      [],
            "providers": {"flatrate": [], "rent": [], "buy": [], "link": None},
            "trailer":   None,
        }

    return {
        "id":          media_id,
        "title":       title,
        "media_type":  media_type,
        **details,
    }


@app.get("/media/{media_id}/poster")
def media_poster(media_id: str):
    """
    Lightweight endpoint — returns only poster + backdrop image URLs for a media item.
    Used to populate the search result grid without fetching full TMDB details.
    """
    if postgres_db is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    items = postgres_db.get_media_by_ids([media_id])
    if not items:
        raise HTTPException(status_code=404, detail="Media item not found.")

    item = items[0]
    meta = item.get("metadata") or {}
    if isinstance(meta, str):
        import json as _json
        try:
            meta = _json.loads(meta)
        except Exception:
            meta = {}
    year = meta.get("year") or meta.get("release_year")
    year = int(year) if year else None

    try:
        images = get_poster_images(item["title"], year, item["media_type"])
    except Exception as exc:
        logger.error(f"Poster fetch failed for '{item['title']}': {exc}")
        images = {"poster": None, "backdrop": None}

    return {"id": media_id, **images}


@app.get("/landing")
def landing():
    """
    Returns trending movies, trending TV shows, and upcoming movies from TMDB.
    Used to populate the Netflix-style landing page hero + rows.
    Results are cached in-memory for 24 h.
    """
    try:
        return get_landing_data()
    except Exception as exc:
        logger.error(f"Landing data error: {exc}", exc_info=True)
        return {"hero": [], "trending_movies": [], "trending_tv": [], "upcoming": []}


if __name__ == "__main__":
    import uvicorn
    # Pull port from environment (standard for Docker/Cloud) or default to 8000
    port = int(os.getenv("PORT", 8000))
    # host 0.0.0.0 is required for Docker and external access
    # reload=True is great for dev, but usually False in prod
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)