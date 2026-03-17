"""
Query Intelligence Layer for VibeCheck Finder.

Parses a raw user query to extract:
  - media_type  : "tv_show" | "book" | None  (DB values)
  - year        : int | None
  - genre       : canonical genre string | None  (always applied as filter)
  - clean_query : noise-free query used for semantic embedding
  - intent      : "title" | "vibe"

Genre filter strategy
---------------------
Genre is ALWAYS applied as a hard filter when detected.
When the user says "documentary about X" they explicitly want documentaries.
When the user says "sci-fi about multiverse" they want sci-fi.
If the DB lacks content matching both genre + concept the result set will be
small — that is accurate behaviour, not a bug.

Clean query strategy
--------------------
- Strip media-type tokens ("movie", "tv show", "documentary" …)
- Strip genre keyword (expansion text provides semantic anchor instead)
- Strip year + connector words ("from 2019")
- Strip filler / structural words ("a", "an", "the", "about", "where" …)
- For pure genre queries: embed the FULL expansion text
- For genre + context: embed "[remaining concept] [3-word genre hint]"
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# Genre map  →  (canonical_genre_for_filter, semantic_expansion_text)
# ---------------------------------------------------------------------------
_GENRE_MAP: Dict[str, Tuple[str, str]] = {
    "sci fi":          ("Scifi", "science fiction futuristic space aliens technology robots dystopian cyberpunk time travel parallel universe"),
    "sci-fi":          ("Scifi", "science fiction futuristic space aliens technology robots dystopian cyberpunk time travel parallel universe"),
    "scifi":           ("Scifi", "science fiction futuristic space aliens technology robots dystopian cyberpunk time travel parallel universe"),
    "science fiction": ("Scifi", "science fiction futuristic space aliens technology robots dystopian cyberpunk time travel parallel universe"),
    "horror":          ("horror", "horror scary terrifying dark supernatural monsters evil haunted fear cursed psychological"),
    "thriller":        ("thriller", "thriller suspense tension dangerous chase conspiracy mystery crime intense"),
    "mystery":         ("mystery", "mystery detective clues investigation secrets suspense whodunit cold case"),
    "crime":           ("crime", "crime murder detective investigation police thriller serial killer forensic"),
    "comedy":          ("comedy", "comedy funny humor laugh witty jokes lighthearted entertaining sitcom"),
    "drama":           ("drama", "drama emotional conflict relationships struggles life family personal"),
    "action":          ("action", "action adventure fight battle combat hero chase explosions stunts"),
    "romance":         ("romance", "romance love relationship passionate heartbreak couple dating emotional"),
    "documentary":     ("Documentation", "documentary real events history facts investigation journalism true story"),
    "animation":       ("animation", "animation animated cartoon family children colorful imaginative"),
    "fantasy":         ("fantasy", "fantasy magic wizards dragons mythical creatures supernatural epic world"),
    "adventure":       ("adventure", "adventure journey quest exploration exciting travel discovery"),
    "biography":       ("biography", "biography life story real person history achievement struggle"),
    "historical":      ("historical", "historical period drama history war past era true events"),
    "anime":           ("anime", "anime japanese animation manga characters fantasy action"),
    "superhero":       ("superhero", "superhero powers hero villain comic book action save world"),
    "war":             ("war", "war military battle soldiers conflict combat survival patriotism"),
    "sport":           ("sport", "sports athlete competition team tournament victory underdog training"),
    "sports":          ("sport", "sports athlete competition team tournament victory underdog training"),
    "western":         ("western", "western cowboys frontier outlaws sheriff gunfight desert justice"),
    "musical":         ("musical", "musical songs singing dancing performance theater stage"),
    "family":          ("family", "family children wholesome heartwarming relationship parents love"),
}

# Regex to detect any genre keyword (longest match first)
_GENRE_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(k) for k in sorted(_GENRE_MAP, key=len, reverse=True)) + r')\b',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Media-type patterns — map to actual DB values ("tv_show" / "book")
# ---------------------------------------------------------------------------
_MOVIE_PATTERNS = re.compile(
    r'\b(movie|film|cinema|feature|flick)\b', re.IGNORECASE
)
_TV_PATTERNS = re.compile(
    r'\b(tv\s*show|tv\s*series|series|show|sitcom|anime|documentary|docuseries|mini[- ]?series|season)\b',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Year patterns
# ---------------------------------------------------------------------------
_YEAR_PATTERN = re.compile(r'\b((?:19|20)\d{2})\b')
_YEAR_CONNECTOR = re.compile(
    r'\b(?:from|in|of|released|made|year)\s+((?:19|20)\d{2})\b', re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Vibe / conceptual intent signals
# ---------------------------------------------------------------------------
_VIBE_SIGNALS = re.compile(
    r'\b('
    r'about|where|when|who|which|feel|feeling|feelings|feels|vibe|vibes|'
    r'mood|emotional|emotion|similar\s+to|like\s+(?:a|an|the)|reminds?|'
    r'dark|funny|sad|happy|scary|creepy|heartbreak|heartbreaking|'
    r'inspiring|uplifting|romantic|romance|comedy|thriller|horror|'
    r'mystery|coming.of.age|nostalg|wholesome|twisted|mind.?blow|'
    r'confusing|philosophical|thought.?provok|binge|underrated|'
    r'based\s+on|true\s+story|real\s+event|discover|journey|'
    r'struggle|redemption|revenge|survival|love|loss|grief|'
    r'something|anything|recommend|suggest|find\s+me|show\s+me|give\s+me'
    r')\b',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Structural strip tokens — removed before embedding
# ---------------------------------------------------------------------------
_STRIP_TOKENS = re.compile(
    r'\b('
    # media format words
    r'movie|film|cinema|feature|flick|'
    r'tv\s*show|tv\s*series|series|show|sitcom|documentary|docuseries|'
    r'mini[- ]?series|anime|'
    # temporal connectors
    r'from|released|made|year|'
    # query connector phrases
    r'based\s+on|that\s+is|which\s+is|set\s+in|'
    r'about\s+an?\b|about\s+the\b|'
    r'a\s+show|a\s+movie|a\s+film|a\s+series'
    r')\b',
    re.IGNORECASE,
)

# Filler / stop words that add noise after structural stripping
_FILLER = re.compile(
    r'\b(a|an|the|is|are|was|were|has|have|had|be|been|'
    r'it|its|that|this|these|those|'
    r'with|for|and|or|but|on|at|to|of|in|by|as|so|if|up|'
    r'where|which|who|when|how|what|'
    r'me|my|us|we|i|he|she|they|them|their|our|your|'
    r'about|just|very|really|quite|some|any)\b',
    re.IGNORECASE,
)


@dataclass
class ParsedQuery:
    original: str
    clean_query: str
    media_type: Optional[str]   # "tv_show" | "book" | None  (actual DB values)
    year: Optional[int]
    genre: Optional[str]        # canonical genre for hard filter (always applied)
    intent: str                 # "title" | "vibe"


def parse(raw_query: str) -> ParsedQuery:
    """
    Parse a raw user query into structured components.

    Args:
        raw_query: The original query string from the user.

    Returns:
        ParsedQuery with extracted parameters and cleaned query text.
    """
    q = raw_query.strip()

    # --- Extract media type --------------------------------------------------
    # DB stores media_type as "tv_show" (TV/documentaries) or "book" (movies).
    media_type: Optional[str] = None
    if _TV_PATTERNS.search(q):
        media_type = "tv_show"
    elif _MOVIE_PATTERNS.search(q):
        media_type = "book"

    # --- Extract year --------------------------------------------------------
    year: Optional[int] = None
    connector_match = _YEAR_CONNECTOR.search(q)
    if connector_match:
        year = int(connector_match.group(1))
    else:
        year_match = _YEAR_PATTERN.search(q)
        if year_match:
            year = int(year_match.group(1))

    # --- Detect genre --------------------------------------------------------
    genre: Optional[str] = None
    genre_expansion: Optional[str] = None
    genre_match = _GENRE_PATTERN.search(q)
    if genre_match:
        matched_keyword = genre_match.group(1).lower()
        canonical, expansion = _GENRE_MAP[matched_keyword]
        genre = canonical
        genre_expansion = expansion

    # --- Build clean query ---------------------------------------------------
    clean = q

    # 1. Remove year with optional connector
    if year:
        clean = re.sub(
            rf'\b(?:from|in|of|released|made|year\s+)?{year}\b', '', clean,
            flags=re.IGNORECASE
        )

    # 2. Remove structural tokens (media format, connector phrases)
    clean = _STRIP_TOKENS.sub('', clean)

    # 3. Remove the detected genre keyword (expansion text replaces it)
    if genre_match:
        clean = re.sub(re.escape(genre_match.group(1)), '', clean, flags=re.IGNORECASE)

    # 4. Strip filler/stop words to surface the semantic core
    clean = _FILLER.sub('', clean)

    # 5. Collapse whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()

    # --- Apply genre expansion -----------------------------------------------
    # Pure genre query ("sci fi") → FULL expansion for rich semantic vector.
    # Genre + concept ("sci-fi politician") → SHORT 3-word hint so the
    # user's specific concept dominates the embedding.
    if genre_expansion:
        if clean:
            short_hint = " ".join(genre_expansion.split()[:3])
            clean = f"{clean} {short_hint}"
        else:
            clean = genre_expansion

    # Fall back to original if all cleaning produced nothing
    if not clean:
        clean = q

    # --- Detect intent -------------------------------------------------------
    tokens = clean.split()
    has_vibe_signal = bool(_VIBE_SIGNALS.search(q))

    if genre or has_vibe_signal or len(tokens) > 4:
        intent = "vibe"
    else:
        intent = "title"

    return ParsedQuery(
        original=q,
        clean_query=clean,
        media_type=media_type,
        year=year,
        genre=genre,
        intent=intent,
    )
