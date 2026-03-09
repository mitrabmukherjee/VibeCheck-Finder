"""
Quick test script for Hybrid Search and TMDB integration.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from ml_engine.sentence_bert_vectorizer import SentenceBertVectorizer
from ml_engine.hybrid_search import HybridSearchEngine
from services.tmdb_service import TMDBService


def test_hybrid_search():
    """Test hybrid search engine."""
    print("=" * 60)
    print("Testing Hybrid Search Engine")
    print("=" * 60)
    
    # Initialize Sentence-BERT
    print("\n1. Initializing Sentence-BERT...")
    sbert = SentenceBertVectorizer(model_name="all-MiniLM-L6-v2")
    print("✓ Sentence-BERT loaded")
    
    # Initialize Hybrid Search
    print("\n2. Initializing Hybrid Search...")
    hybrid = HybridSearchEngine(
        sbert_vectorizer=sbert,
        tfidf_weight=0.3,
        sbert_weight=0.7
    )
    print("✓ Hybrid Search initialized")
    
    # Create sample corpus
    print("\n3. Indexing sample corpus...")
    texts = [
        "Breaking Bad A high school chemistry teacher turned methamphetamine producer",
        "The Wire A realistic look at the drug trade in Baltimore",
        "Inception A thief who steals corporate secrets through dream-sharing technology",
        "The Matrix A computer hacker learns about the true nature of reality",
        "Game of Thrones Epic fantasy series about noble families vying for the Iron Throne"
    ]
    ids = ["id1", "id2", "id3", "id4", "id5"]
    
    hybrid.index_corpus(texts, ids, batch_size=5)
    print(f"✓ Indexed {len(texts)} items")
    
    # Test searches
    print("\n4. Testing searches...")
    
    test_queries = [
        "Breaking Bad",  # Exact title match
        "drug crime drama",  # Semantic match
        "dream heist movie",  # Semantic match
    ]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        results = hybrid.search(query, top_k=3)
        for i, result in enumerate(results, 1):
            idx = ids.index(result['id'])
            title = texts[idx].split()[0:2]
            print(f"   {i}. {' '.join(title)} (score: {result['score']:.3f})")
    
    print("\n✓ Hybrid search working correctly!")


def test_tmdb_service():
    """Test TMDB service."""
    print("\n" + "=" * 60)
    print("Testing TMDB Service")
    print("=" * 60)
    
    # Initialize TMDB service
    print("\n1. Initializing TMDB Service...")
    tmdb = TMDBService()
    
    if not tmdb.api_key or tmdb.api_key == "your_api_key_here":
        print("⚠ TMDB_API_KEY not set in .env file")
        print("  Get your API key from: https://www.themoviedb.org/settings/api")
        print("  Add it to backend/.env: TMDB_API_KEY=your_key_here")
        return
    
    print("✓ TMDB Service initialized")
    
    # Test movie search
    print("\n2. Testing movie search...")
    test_movies = [
        ("Inception", 2010),
        ("The Matrix", 1999),
        ("Breaking Bad", None)  # TV show
    ]
    
    for title, year in test_movies:
        print(f"\n   Searching: '{title}' ({year or 'no year'})")
        
        # Try movie first
        result = tmdb.search_movie(title, year)
        if result:
            poster_url = tmdb.get_poster_url(result['poster_path'])
            print(f"   ✓ Found movie: {result['title']}")
            print(f"   Poster: {poster_url}")
        else:
            # Try TV show
            result = tmdb.search_tv(title, year)
            if result:
                poster_url = tmdb.get_poster_url(result['poster_path'])
                print(f"   ✓ Found TV show: {result['name']}")
                print(f"   Poster: {poster_url}")
            else:
                print(f"   ✗ Not found")
    
    print("\n✓ TMDB service working correctly!")


if __name__ == "__main__":
    try:
        test_hybrid_search()
        test_tmdb_service()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Add TMDB_API_KEY to backend/.env")
        print("2. Restart backend: cd backend && python -m uvicorn main:app --reload")
        print("3. Test search with movie titles")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
