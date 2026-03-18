"""
TMDB (The Movie Database) integration.

Provides on-demand enrichment for media items:
  - Cast members (top 10)
  - Streaming / watch providers (region-aware)
  - Trailer YouTube link

All results are cached in-memory for 24 h.
Uses the `requests` library which handles Windows TCP connections reliably.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests as _requests

logger = logging.getLogger(__name__)

TMDB_BASE       = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
CACHE_TTL       = 60 * 60 * 24  # 24 hours

# ---------------------------------------------------------------------------
# Lazy env-var accessors (load_dotenv() in main.py runs before the first call)
# ---------------------------------------------------------------------------
def _api_key()      -> str: return os.getenv("TMDB_API_KEY", "")
def _access_token() -> str: return os.getenv("TMDB_ACCESS_TOKEN", "")
def _region()       -> str: return os.getenv("TMDB_REGION", "IN")

# ---------------------------------------------------------------------------
# Persistent requests session — more reliable than httpx on Windows
# ---------------------------------------------------------------------------
_session: Optional[_requests.Session] = None

def _get_session() -> _requests.Session:
    global _session
    if _session is None:
        _session = _requests.Session()
    return _session

# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------
_cache: Dict[str, Dict[str, Any]] = {}

def _cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < CACHE_TTL:
        return entry["data"]
    return None

def _cache_set(key: str, data: Any) -> None:
    _cache[key] = {"data": data, "ts": time.time()}

# ---------------------------------------------------------------------------
# HTTP helper with retries
# ---------------------------------------------------------------------------
def _headers() -> Dict[str, str]:
    token = _access_token()
    h = {"accept": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h

def _get(url: str, params: Dict[str, Any]) -> _requests.Response:
    """GET with up to 3 retries on transient connection errors."""
    last_exc: Exception = RuntimeError("no attempts made")
    for attempt in range(3):
        try:
            r = _get_session().get(url, params=params, headers=_headers(), timeout=10)
            r.raise_for_status()
            return r
        except (_requests.exceptions.ConnectionError,
                _requests.exceptions.ChunkedEncodingError) as exc:
            last_exc = exc
            time.sleep(0.5 * (attempt + 1))
        except _requests.exceptions.HTTPError:
            raise
    raise last_exc

# ---------------------------------------------------------------------------
# TMDB media type helper
# ---------------------------------------------------------------------------
def _tmdb_type(media_type: str) -> str:
    return "tv" if media_type == "tv_show" else "movie"

# ---------------------------------------------------------------------------
# Search — title + optional year → tmdb_id
# ---------------------------------------------------------------------------
def search_tmdb(title: str, year: Optional[int], media_type: str) -> Optional[int]:
    cache_key = f"search::{media_type}::{title}::{year}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    kind = _tmdb_type(media_type)
    params: Dict[str, Any] = {"query": title, "api_key": _api_key()}
    if year:
        params["year" if kind == "movie" else "first_air_date_year"] = year

    try:
        r = _get(f"{TMDB_BASE}/search/{kind}", params)
        results = r.json().get("results", [])
        if results:
            tmdb_id = results[0]["id"]
            _cache_set(cache_key, tmdb_id)
            return tmdb_id

        # Retry without year
        if year:
            params.pop("year", None)
            params.pop("first_air_date_year", None)
            r = _get(f"{TMDB_BASE}/search/{kind}", params)
            results = r.json().get("results", [])
            if results:
                tmdb_id = results[0]["id"]
                _cache_set(cache_key, tmdb_id)
                return tmdb_id

    except Exception as exc:
        logger.warning(f"TMDB search failed for '{title}': {exc}")

    _cache_set(cache_key, None)
    return None

# ---------------------------------------------------------------------------
# Cast
# ---------------------------------------------------------------------------
def get_cast(tmdb_id: int, media_type: str, limit: int = 10) -> List[Dict[str, Any]]:
    cache_key = f"cast::{media_type}::{tmdb_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    kind = _tmdb_type(media_type)
    try:
        r = _get(f"{TMDB_BASE}/{kind}/{tmdb_id}/credits", {"api_key": _api_key()})
        raw_cast = r.json().get("cast", [])
        cast = [
            {
                "name":      m.get("name", ""),
                "character": m.get("character", ""),
                "photo":     f"{TMDB_IMAGE_BASE}/w185{m['profile_path']}"
                             if m.get("profile_path") else None,
            }
            for m in raw_cast[:limit]
        ]
        _cache_set(cache_key, cast)
        return cast
    except Exception as exc:
        logger.warning(f"TMDB cast failed (id={tmdb_id}): {exc}")
        return []

# ---------------------------------------------------------------------------
# Watch providers
# ---------------------------------------------------------------------------
def get_providers(tmdb_id: int, media_type: str) -> Dict[str, Any]:
    cache_key = f"providers::{media_type}::{tmdb_id}::{_region()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    kind = _tmdb_type(media_type)
    try:
        r = _get(f"{TMDB_BASE}/{kind}/{tmdb_id}/watch/providers", {"api_key": _api_key()})
        region_data = r.json().get("results", {}).get(_region(), {})

        def _fmt(providers: List[Dict]) -> List[Dict]:
            return [
                {
                    "name": p.get("provider_name", ""),
                    "logo": f"{TMDB_IMAGE_BASE}/w92{p['logo_path']}" if p.get("logo_path") else None,
                }
                for p in providers
            ]

        result = {
            "flatrate": _fmt(region_data.get("flatrate", [])),
            "rent":     _fmt(region_data.get("rent", [])),
            "buy":      _fmt(region_data.get("buy", [])),
            "link":     region_data.get("link"),
        }
        _cache_set(cache_key, result)
        return result
    except Exception as exc:
        logger.warning(f"TMDB providers failed (id={tmdb_id}): {exc}")
        return {"flatrate": [], "rent": [], "buy": [], "link": None}

# ---------------------------------------------------------------------------
# Trailer
# ---------------------------------------------------------------------------
def get_trailer(tmdb_id: int, media_type: str) -> Optional[str]:
    cache_key = f"trailer::{media_type}::{tmdb_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    kind = _tmdb_type(media_type)
    try:
        r = _get(f"{TMDB_BASE}/{kind}/{tmdb_id}/videos", {"api_key": _api_key()})
        videos = r.json().get("results", [])
        for v in videos:
            if v.get("site") == "YouTube" and v.get("type") == "Trailer":
                url = f"https://www.youtube.com/watch?v={v['key']}"
                _cache_set(cache_key, url)
                return url
        for v in videos:
            if v.get("site") == "YouTube":
                url = f"https://www.youtube.com/watch?v={v['key']}"
                _cache_set(cache_key, url)
                return url
    except Exception as exc:
        logger.warning(f"TMDB trailer failed (id={tmdb_id}): {exc}")

    _cache_set(cache_key, None)
    return None

# ---------------------------------------------------------------------------
# Landing page: trending + upcoming content
# ---------------------------------------------------------------------------
def get_landing_data() -> Dict[str, Any]:
    """Fetch trending movies, trending TV, and upcoming movies from TMDB."""
    cache_key = "landing_data"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    def _fmt(item: Dict, media_type: str) -> Dict:
        raw_date = item.get("release_date") or item.get("first_air_date") or ""
        return {
            "tmdb_id":   item.get("id"),
            "title":     item.get("title") or item.get("name", ""),
            "overview":  item.get("overview", ""),
            "backdrop":  f"{TMDB_IMAGE_BASE}/original{item['backdrop_path']}"
                         if item.get("backdrop_path") else None,
            "poster":    f"{TMDB_IMAGE_BASE}/w342{item['poster_path']}"
                         if item.get("poster_path") else None,
            "rating":    round(item.get("vote_average", 0), 1),
            "year":      raw_date[:4] if raw_date else "",
            "media_type": media_type,
        }

    try:
        r = _get(f"{TMDB_BASE}/trending/movie/week", {"api_key": _api_key(), "language": "en-US"})
        trending_movies = [
            _fmt(i, "movie") for i in r.json().get("results", [])[:16]
            if i.get("poster_path")
        ]
        time.sleep(0.2)

        r = _get(f"{TMDB_BASE}/trending/tv/week", {"api_key": _api_key(), "language": "en-US"})
        trending_tv = [
            _fmt(i, "tv") for i in r.json().get("results", [])[:16]
            if i.get("poster_path")
        ]
        time.sleep(0.2)

        r = _get(f"{TMDB_BASE}/movie/upcoming", {
            "api_key": _api_key(), "language": "en-US", "region": _region()
        })
        upcoming = [
            _fmt(i, "movie") for i in r.json().get("results", [])[:16]
            if i.get("poster_path")
        ]

        # Hero candidates: top trending with backdrops
        hero_candidates = [i for i in trending_movies if i.get("backdrop")]
        result = {
            "hero":             hero_candidates[:6],
            "trending_movies":  trending_movies,
            "trending_tv":      trending_tv,
            "upcoming":         upcoming,
        }
        _cache_set(cache_key, result)
        return result

    except Exception as exc:
        logger.warning(f"Landing data fetch failed: {exc}")
        return {"hero": [], "trending_movies": [], "trending_tv": [], "upcoming": []}


# ---------------------------------------------------------------------------
# Public: fetch everything at once
# ---------------------------------------------------------------------------
def get_full_details(title: str, year: Optional[int], media_type: str) -> Dict[str, Any]:
    tmdb_id = search_tmdb(title, year, media_type)
    if not tmdb_id:
        return {"tmdb_id": None, "cast": [], "providers": {"flatrate": [], "rent": [], "buy": [], "link": None}, "trailer": None}

    cast      = get_cast(tmdb_id, media_type)
    time.sleep(0.2)
    providers = get_providers(tmdb_id, media_type)
    time.sleep(0.2)
    trailer   = get_trailer(tmdb_id, media_type)

    return {"tmdb_id": tmdb_id, "cast": cast, "providers": providers, "trailer": trailer}
