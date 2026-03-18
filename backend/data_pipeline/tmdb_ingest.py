"""
TMDB Dataset Ingestion
======================
Fetches trending, upcoming, and top-rated movies + TV shows from TMDB
and adds them to the local PostgreSQL + vector database.

What it pulls:
  - Trending movies  (weekly, pages 1-5  = up to 100 items)
  - Trending TV      (weekly, pages 1-5  = up to 100 items)
  - Upcoming movies  (pages 1-3          = up to 60 items)
  - Top-rated movies (pages 1-5          = up to 100 items)
  - Top-rated TV     (pages 1-5          = up to 100 items)

Deduplication:
  Normalised title comparison against every existing title in the DB.
  Items already present are skipped, only genuinely new ones are inserted.

Embeddings:
  New items are embedded with the SAME SBERT model already in use
  (all-mpnet-base-v2 → 768-dim) and APPENDED to the existing vector store.
  The running server does NOT need to be restarted; it will pick up new
  embeddings on the next query automatically via the FileVectorDatabase.

Usage:
    cd backend
    python -m data_pipeline.tmdb_ingest
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
import uuid
from typing import Any, Dict, List, Optional, Set

import numpy as np
import requests

# Allow running as a script from the backend directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from database.postgres import PostgresDatabase
from database.file_vector_db import FileVectorDatabase
from ml_engine.ml_engine import MLEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config — read after load_dotenv()
# ---------------------------------------------------------------------------
TMDB_API_KEY    = os.getenv("TMDB_API_KEY", "")
TMDB_BASE       = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
EMBEDDINGS_PATH = os.getenv("EMBEDDINGS_PATH", "embeddings")
SBERT_MODEL     = os.getenv("SBERT_MODEL_NAME", "all-mpnet-base-v2")
VECTOR_SIZE     = int(os.getenv("VECTOR_SIZE", "768"))
BATCH_EMBED     = 32   # items per SBERT batch
REQUEST_DELAY   = 0.25  # seconds between TMDB calls (rate-limit safety)

# ---------------------------------------------------------------------------
# TMDB genre-ID → name maps (fetched fresh at runtime)
# ---------------------------------------------------------------------------
_GENRE_MAP: Dict[int, str] = {}


def _fetch_genre_map() -> None:
    """Populate _GENRE_MAP from TMDB's genre lists."""
    for kind in ("movie", "tv"):
        try:
            r = requests.get(
                f"{TMDB_BASE}/genre/{kind}/list",
                params={"api_key": TMDB_API_KEY},
                timeout=10,
            )
            r.raise_for_status()
            for g in r.json().get("genres", []):
                _GENRE_MAP[g["id"]] = g["name"]
        except Exception as exc:
            logger.warning(f"Could not fetch {kind} genres: {exc}")


def _genre_name(genre_ids: List[int]) -> str:
    """Return the first genre name for a list of TMDB genre IDs."""
    for gid in genre_ids:
        name = _GENRE_MAP.get(gid)
        if name:
            return name
    return ""


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------
def _norm(title: str) -> str:
    """Lowercase + strip all non-alphanumeric characters for comparison."""
    return re.sub(r"[^a-z0-9]", "", title.lower())


def _build_existing_set(db: PostgresDatabase) -> Set[str]:
    """Return a set of normalised titles already in the DB."""
    logger.info("Loading existing titles for deduplication …")
    all_items = db.get_all_media()
    existing = {_norm(item["title"]) for item in all_items}
    logger.info(f"  {len(existing)} titles already in DB")
    return existing


# ---------------------------------------------------------------------------
# TMDB fetch helpers
# ---------------------------------------------------------------------------
_session = requests.Session()


def _get(endpoint: str, params: Dict[str, Any] = {}) -> Dict[str, Any]:
    """GET a TMDB endpoint with the API key pre-injected."""
    p = {"api_key": TMDB_API_KEY, **params}
    for attempt in range(3):
        try:
            r = _session.get(f"{TMDB_BASE}{endpoint}", params=p, timeout=10)
            r.raise_for_status()
            return r.json()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError) as exc:
            logger.warning(f"Retrying ({attempt+1}/3) {endpoint}: {exc}")
            time.sleep(0.5 * (attempt + 1))
    return {}


def _raw_to_item(raw: Dict[str, Any], kind: str) -> Optional[Dict[str, Any]]:
    """
    Convert a raw TMDB result dict to our internal media item format.
    Returns None if the item lacks a title or description.
    """
    title       = (raw.get("title") or raw.get("name") or "").strip()
    description = (raw.get("overview") or "").strip()

    if not title or not description:
        return None

    media_type = "tv_show" if kind == "tv" else "book"
    year_str   = raw.get("release_date") or raw.get("first_air_date") or ""
    year: Optional[int] = None
    try:
        year = int(year_str[:4]) if year_str else None
    except ValueError:
        pass

    poster = raw.get("poster_path")
    metadata: Dict[str, Any] = {
        "genre":  _genre_name(raw.get("genre_ids", [])),
        "rating": round(raw.get("vote_average", 0.0), 1),
        "is_latest": True,
    }
    if year:
        metadata["year"] = year
    if poster:
        metadata["thumbnail_url"] = f"{TMDB_IMAGE_BASE}/w342{poster}"

    return {
        "id":          str(uuid.uuid4()),
        "title":       title[:500],
        "description": description[:5000],
        "media_type":  media_type,
        "metadata":    metadata,
    }


def _fetch_pages(endpoint: str, kind: str, pages: int) -> List[Dict[str, Any]]:
    """Fetch multiple pages from a TMDB list endpoint."""
    items: List[Dict[str, Any]] = []
    for page in range(1, pages + 1):
        data = _get(endpoint, {"page": page})
        for raw in data.get("results", []):
            item = _raw_to_item(raw, kind)
            if item:
                items.append(item)
        time.sleep(REQUEST_DELAY)
    return items


# ---------------------------------------------------------------------------
# Main ingestion sources
# ---------------------------------------------------------------------------
def collect_from_tmdb() -> List[Dict[str, Any]]:
    """Pull all configured TMDB sources and return a combined list."""
    sources = [
        # (endpoint,                   kind,    pages, label)
        ("/trending/movie/week",        "movie", 5,     "Trending movies"),
        ("/trending/tv/week",           "tv",    5,     "Trending TV"),
        ("/movie/upcoming",             "movie", 3,     "Upcoming movies"),
        ("/movie/top_rated",            "movie", 5,     "Top-rated movies"),
        ("/tv/top_rated",               "tv",    5,     "Top-rated TV"),
    ]

    all_items: List[Dict[str, Any]] = []
    for endpoint, kind, pages, label in sources:
        logger.info(f"Fetching {label} ({pages} pages) …")
        batch = _fetch_pages(endpoint, kind, pages)
        logger.info(f"  → {len(batch)} items fetched")
        all_items.extend(batch)

    return all_items


# ---------------------------------------------------------------------------
# Embedding helpers — append-only, no full rebuild
# ---------------------------------------------------------------------------
def _append_embeddings(
    new_ids: List[str],
    new_texts: List[str],
    ml_engine: MLEngine,
    vector_db: FileVectorDatabase,
) -> None:
    """Generate embeddings for new items and append them to the vector store."""
    logger.info(f"Generating embeddings for {len(new_texts)} new items …")
    embeddings = ml_engine.compute_embeddings(new_texts, new_ids, batch_size=BATCH_EMBED)
    logger.info(f"  Embedding shape: {embeddings.shape}")

    items = [
        (new_ids[i], embeddings[i].tolist(), {})
        for i in range(len(new_ids))
    ]

    if hasattr(vector_db, "batch_insert"):
        vector_db.batch_insert(items)
    else:
        for item_id, vec, meta in items:
            vector_db.insert(item_id, vec, meta)

    logger.info("  Embeddings appended to vector store ✓")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    logger.info("=" * 60)
    logger.info("  TMDB Dataset Ingestion")
    logger.info("=" * 60)

    if not TMDB_API_KEY:
        logger.error("TMDB_API_KEY is not set in .env — aborting.")
        sys.exit(1)

    # ── 1. Fetch genre map ─────────────────────────────────────────────────
    logger.info("Fetching TMDB genre map …")
    _fetch_genre_map()
    logger.info(f"  {len(_GENRE_MAP)} genres loaded")

    # ── 2. Connect to DB and build dedup set ───────────────────────────────
    db = PostgresDatabase()
    existing = _build_existing_set(db)

    # ── 3. Collect from TMDB ───────────────────────────────────────────────
    candidates = collect_from_tmdb()
    logger.info(f"\nTotal TMDB items collected : {len(candidates)}")

    # ── 4. Dedup within this batch (by norm title) ─────────────────────────
    seen_this_run: Set[str] = set()
    new_items: List[Dict[str, Any]] = []
    skipped_existing = 0
    skipped_dup      = 0

    for item in candidates:
        norm = _norm(item["title"])
        if norm in existing:
            skipped_existing += 1
        elif norm in seen_this_run:
            skipped_dup += 1
        else:
            seen_this_run.add(norm)
            new_items.append(item)

    logger.info(f"Already in DB (skipped)    : {skipped_existing}")
    logger.info(f"Duplicates in batch        : {skipped_dup}")
    logger.info(f"Genuinely new items        : {len(new_items)}")

    if not new_items:
        logger.info("\nNothing new to add — database is up to date.")
        db.close()
        return

    # ── 5. Insert into PostgreSQL ──────────────────────────────────────────
    logger.info(f"\nInserting {len(new_items)} items into PostgreSQL …")
    inserted_ids = db.batch_insert_media(new_items)
    logger.info(f"  Inserted {len(inserted_ids)} items ✓")
    db.close()

    # ── 6. Generate + append embeddings ───────────────────────────────────
    logger.info(f"\nInitialising SBERT model ({SBERT_MODEL}) …")
    ml_engine = MLEngine(
        vectorizer_path="models",
        embeddings_path=EMBEDDINGS_PATH,
        vectorizer_type="sbert",
        model_name=SBERT_MODEL,
    )

    vector_db = FileVectorDatabase(
        storage_path=EMBEDDINGS_PATH,
        vector_size=VECTOR_SIZE,
    )

    texts = [f"{item['title']}. {item['description']}" for item in new_items]
    _append_embeddings(inserted_ids, texts, ml_engine, vector_db)

    # ── 7. Summary ─────────────────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 60)
    logger.info("  Ingestion complete!")
    logger.info(f"  New items added : {len(inserted_ids)}")
    logger.info(f"  Vector DB size  : {vector_db.count()} total")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Restart the backend server to reload the hybrid search corpus.")


if __name__ == "__main__":
    main()
