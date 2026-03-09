"""
TMDB API Service for fetching movie/TV show posters.

This service integrates with The Movie Database (TMDB) API to fetch
poster images for media items.
"""

import os
import logging
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class TMDBService:
    """Service for interacting with TMDB API."""
    
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize TMDB service.
        
        Args:
            api_key: TMDB API key (reads from TMDB_API_KEY env var if not provided)
        """
        self.api_key = api_key or os.getenv("TMDB_API_KEY")
        if not self.api_key:
            logger.warning("TMDB_API_KEY not set. Poster fetching will be disabled.")
        
        self.session = requests.Session()
        self.session.params = {"api_key": self.api_key}
    
    def search_movie(self, title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Search for a movie by title.
        
        Args:
            title: Movie title
            year: Optional release year for better matching
        
        Returns:
            Movie data dict or None if not found
        """
        if not self.api_key:
            return None
        
        try:
            params = {"query": title}
            if year:
                params["year"] = year
            
            response = self.session.get(
                f"{self.BASE_URL}/search/movie",
                params=params,
                timeout=5
            )
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if results:
                return results[0]  # Return first match
            return None
            
        except Exception as e:
            logger.error(f"Error searching movie '{title}': {e}")
            return None
    
    def search_tv(self, title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Search for a TV show by title.
        
        Args:
            title: TV show title
            year: Optional first air year for better matching
        
        Returns:
            TV show data dict or None if not found
        """
        if not self.api_key:
            return None
        
        try:
            params = {"query": title}
            if year:
                params["first_air_date_year"] = year
            
            response = self.session.get(
                f"{self.BASE_URL}/search/tv",
                params=params,
                timeout=5
            )
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if results:
                return results[0]  # Return first match
            return None
            
        except Exception as e:
            logger.error(f"Error searching TV show '{title}': {e}")
            return None
    
    def get_poster_url(
        self,
        poster_path: str,
        size: str = "w500"
    ) -> str:
        """
        Get full poster URL from poster path.
        
        Args:
            poster_path: Poster path from TMDB API (e.g., "/abc123.jpg")
            size: Image size (w92, w154, w185, w342, w500, w780, original)
        
        Returns:
            Full poster URL
        """
        return f"{self.IMAGE_BASE_URL}/{size}{poster_path}"
    
    def fetch_poster_for_media(
        self,
        title: str,
        media_type: str,
        year: Optional[int] = None,
        size: str = "w500"
    ) -> Optional[str]:
        """
        Fetch poster URL for a media item.
        
        Args:
            title: Media title
            media_type: "movie" or "tv_show"
            year: Optional year for better matching
            size: Image size
        
        Returns:
            Poster URL or None if not found
        """
        if not self.api_key:
            return None
        
        # Search based on media type
        if media_type == "tv_show":
            result = self.search_tv(title, year)
        else:
            result = self.search_movie(title, year)
        
        if result and result.get("poster_path"):
            return self.get_poster_url(result["poster_path"], size)
        
        return None
