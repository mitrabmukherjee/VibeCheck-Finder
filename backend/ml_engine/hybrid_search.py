"""
Hybrid Search Engine — tiered priority scoring.

Scoring philosophy
------------------
The engine uses a TWO-TIER priority model instead of a fixed blend:

  Tier 1 — Title Match  (title_score >= TITLE_MATCH_THRESHOLD)
      Any result with a strong title hit is promoted to the top.
      Score = title_score * TITLE_W  +  semantic_score * (1 - TITLE_W)
      These results are sorted among themselves by title_score DESC.

  Tier 2 — Vibe / Semantic  (no strong title match)
      Results are ranked purely by semantic meaning.
      Score = semantic_score * SEMANTIC_W  +  title_score * (1 - SEMANTIC_W)
      The title score acts only as a minor tie-breaker.

Tier 1 results are always placed before Tier 2 results in the final list,
then within each tier results are sorted by their tier score DESC.

A small popularity boost (up to +0.05) is applied after tier scoring so that
highly rated content wins ties within the same tier.
"""

from __future__ import annotations

import json
import logging
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from .query_parser import ParsedQuery

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------

# Minimum title score to be considered a "strong" title match (Tier 1)
TITLE_MATCH_THRESHOLD = 0.82

# Weight given to the title score when a Tier-1 match is being scored
TITLE_W = 0.88

# Weight given to semantic score for Tier-2 (vibe) results
SEMANTIC_W = 0.90

# Maximum popularity boost added to the tier score
MAX_RATING_BOOST = 0.05


class HybridSearchEngine:
    """
    Two-tier hybrid search: title-first when a strong match exists,
    semantic-first otherwise.
    """

    def __init__(
        self,
        title_weight: float = TITLE_W,
        semantic_weight: float = SEMANTIC_W,
    ):
        # Kept as instance attributes so callers can override if needed,
        # but the defaults reflect the tiered strategy.
        self.title_weight = title_weight
        self.semantic_weight = semantic_weight
        self.corpus: List[Dict[str, Any]] = []
        self.title_index: Dict[str, str] = {}  # normalized_title -> media_id

    # ------------------------------------------------------------------
    # Corpus indexing
    # ------------------------------------------------------------------

    def index_corpus(self, media_items: List[Dict[str, Any]]) -> None:
        self.corpus = media_items
        self.title_index = {
            self._normalize(item["title"]): item["id"] for item in media_items
        }

    # ------------------------------------------------------------------
    # Text helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^\w\s]", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def _title_score(self, query: str, title: str) -> float:
        """
        Return a 0-1 similarity score between a query and a media title.

        Scoring ladder (highest wins):
          1.0  — exact match after normalization
          0.97 — query is a near-complete substring of title (ratio > 0.8)
          0.93 — query is a substring of title
          0.93 — title is a substring of query
          0.95+ — all query words present in title words (boosted by fuzzy ratio)
          else  — SequenceMatcher ratio
        """
        q = self._normalize(query)
        t = self._normalize(title)

        if q == t:
            return 1.0

        if q in t:
            ratio = len(q) / max(len(t), 1)
            return 0.97 if ratio > 0.8 else 0.93

        if t in q:
            return 0.93

        fuzzy = SequenceMatcher(None, q, t).ratio()

        q_words = set(q.split())
        t_words = set(t.split())
        if q_words and q_words.issubset(t_words):
            return max(fuzzy, 0.95 if fuzzy > 0.7 else 0.87)

        return fuzzy

    # ------------------------------------------------------------------
    # Popularity boost
    # ------------------------------------------------------------------

    @staticmethod
    def _rating_boost(item: Dict[str, Any]) -> float:
        try:
            metadata = item.get("metadata", {})
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            if not isinstance(metadata, dict):
                return 0.0
            rating = metadata.get("rating")
            if isinstance(rating, (int, float)) and rating > 5:
                # Scales from 0 at rating=5 up to MAX_RATING_BOOST at rating=10
                return min((rating - 5) / (10 - 5) * MAX_RATING_BOOST, MAX_RATING_BOOST)
        except Exception:
            pass
        return 0.0

    # ------------------------------------------------------------------
    # Main search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        semantic_results: List[Dict[str, Any]],
        top_k: int = 10,
        parsed_query: Optional[ParsedQuery] = None,
    ) -> List[Dict[str, Any]]:
        """
        Re-rank semantic_results using the two-tier priority model.

        Args:
            query:            Raw user query string.
            semantic_results: Results from the vector DB, each a dict with
                              'id' and 'score' keys.
            top_k:            Maximum number of results to return.
            parsed_query:     Optional pre-parsed query from query_parser.parse().
                              When provided, the clean_query is used for title
                              scoring so extracted parameters don't interfere.

        Returns:
            Re-ranked list of result dicts with keys:
              id, score, title_score, semantic_score, tier
        """
        # Use the clean query for title comparison if available
        title_query = parsed_query.clean_query if parsed_query else query

        semantic_map: Dict[str, float] = {
            r["id"]: r["score"] for r in semantic_results
        }

        # Build a fast lookup: id -> corpus item
        corpus_map: Dict[str, Dict[str, Any]] = {
            item["id"]: item for item in self.corpus
        }

        # Compute title scores only for IDs present in semantic results
        # (avoids O(corpus) work when corpus is large)
        candidate_ids = set(semantic_map.keys())

        tier1: List[Dict[str, Any]] = []
        tier2: List[Dict[str, Any]] = []

        for media_id in candidate_ids:
            item = corpus_map.get(media_id)
            title = item["title"] if item else media_id

            t_score = self._title_score(title_query, title)
            s_score = semantic_map.get(media_id, 0.0)
            boost = self._rating_boost(item) if item else 0.0

            if t_score >= TITLE_MATCH_THRESHOLD:
                # Tier 1: title-led scoring
                combined = self.title_weight * t_score + (1 - self.title_weight) * s_score + boost
                tier1.append({
                    "id": media_id,
                    "score": combined,
                    "title_score": t_score,
                    "semantic_score": s_score,
                    "tier": 1,
                })
            else:
                # Tier 2: semantic-led scoring
                combined = self.semantic_weight * s_score + (1 - self.semantic_weight) * t_score + boost
                tier2.append({
                    "id": media_id,
                    "score": combined,
                    "title_score": t_score,
                    "semantic_score": s_score,
                    "tier": 2,
                })

        tier1.sort(key=lambda x: x["score"], reverse=True)
        tier2.sort(key=lambda x: x["score"], reverse=True)

        results = tier1 + tier2
        return results[:top_k]
