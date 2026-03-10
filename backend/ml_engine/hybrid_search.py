"""
Hybrid Search Engine combining title matching with semantic search.

This module provides a lightweight hybrid search that:
1. Uses fuzzy string matching on titles for exact name queries
2. Falls back to semantic search for conceptual queries
3. Combines results with weighted scoring
"""

from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher
import re
import logging

logger = logging.getLogger(__name__)


class HybridSearchEngine:
    """
    Lightweight hybrid search combining title matching with semantic search.
    
    This approach helps retrieve items by exact titles (e.g., "Mean Girls")
    while maintaining semantic search capabilities for conceptual queries.
    """
    
    def __init__(self, title_weight: float = 0.5, semantic_weight: float = 0.5):
        """
        Initialize hybrid search engine.
        
        Args:
            title_weight: Weight for title matching score (0-1)
            semantic_weight: Weight for semantic similarity score (0-1)
        """
        self.title_weight = title_weight
        self.semantic_weight = semantic_weight
        self.corpus: List[Dict[str, Any]] = []
        self.title_index: Dict[str, str] = {}  # normalized_title -> media_id
    
    def index_corpus(self, media_items: List[Dict[str, Any]]) -> None:
        """
        Index media items for title-based search.
        
        Args:
            media_items: List of media dictionaries with 'id' and 'title' fields
        """
        self.corpus = media_items
        self.title_index = {}
        
        for item in media_items:
            normalized_title = self._normalize_text(item['title'])
            self.title_index[normalized_title] = item['id']
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for matching (lowercase, remove special chars).
        
        Args:
            text: Input text
        
        Returns:
            Normalized text
        """
        # Convert to lowercase and remove special characters
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _calculate_title_similarity(self, query: str, title: str) -> float:
        """
        Calculate similarity between query and title using fuzzy matching.
        
        Args:
            query: Search query
            title: Media title
        
        Returns:
            Similarity score (0-1)
        """
        query_norm = self._normalize_text(query)
        title_norm = self._normalize_text(title)
        
        # Exact match - perfect score
        if query_norm == title_norm:
            return 1.0
        
        # Check if query is contained in title (e.g., "bulbul" in "bulbul")
        if query_norm in title_norm:
            # If query is the entire title, give high score
            if len(query_norm) == len(title_norm):
                return 1.0
            # If query is most of the title, still very high
            ratio = len(query_norm) / len(title_norm)
            if ratio > 0.8:
                return 0.95
            return 0.9
        
        # Check if title is contained in query
        if title_norm in query_norm:
            return 0.9
        
        # Use SequenceMatcher for fuzzy matching
        similarity = SequenceMatcher(None, query_norm, title_norm).ratio()
        
        # Boost score if query words are all in title
        query_words = set(query_norm.split())
        title_words = set(title_norm.split())
        if query_words and query_words.issubset(title_words):
            # If all query words match and it's a high ratio, boost significantly
            if similarity > 0.7:
                similarity = max(similarity, 0.95)
            else:
                similarity = max(similarity, 0.85)
        
        return similarity
    
    def search(
        self,
        query: str,
        semantic_results: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining title matching with semantic results.
        
        Args:
            query: Search query
            semantic_results: Results from semantic search with 'id' and 'score'
            top_k: Number of results to return
        
        Returns:
            List of results with combined scores, sorted by relevance
        """
        # Create a map of semantic scores
        semantic_scores = {result['id']: result['score'] for result in semantic_results}
        
        # Calculate title similarity for all items in corpus
        title_scores = {}
        for item in self.corpus:
            media_id = item['id']
            title_sim = self._calculate_title_similarity(query, item['title'])
            title_scores[media_id] = title_sim
        
        # Combine scores
        combined_results = []
        all_ids = set(semantic_scores.keys()) | set(title_scores.keys())
        
        for media_id in all_ids:
            semantic_score = semantic_scores.get(media_id, 0.0)
            title_score = title_scores.get(media_id, 0.0)
            
            # Calculate weighted combined score
            combined_score = (
                self.title_weight * title_score +
                self.semantic_weight * semantic_score
            )
            
            # Apply popularity boost based on rating
            try:
                item = next((item for item in self.corpus if item['id'] == media_id), None)
                if item and 'metadata' in item:
                    metadata = item['metadata']
                    # Handle both dict and potential JSON string
                    if isinstance(metadata, str):
                        import json
                        try:
                            metadata = json.loads(metadata)
                        except:
                            metadata = {}
                    
                    if isinstance(metadata, dict):
                        rating = metadata.get('rating')
                        if rating and isinstance(rating, (int, float)) and rating > 0:
                            # Boost by up to 10% for highly rated content (rating 8-10)
                            rating_boost = min((rating - 5) / 50, 0.1)  # Max 10% boost
                            if rating_boost > 0:
                                combined_score += rating_boost
            except Exception as e:
                # Skip boost if there's any error accessing metadata
                logger.debug(f"Skipping popularity boost for {media_id}: {e}")
                pass
            
            combined_results.append({
                'id': media_id,
                'score': combined_score,
                'title_score': title_score,
                'semantic_score': semantic_score
            })
        
        # Sort by combined score and return top_k
        combined_results.sort(key=lambda x: x['score'], reverse=True)
        return combined_results[:top_k]
