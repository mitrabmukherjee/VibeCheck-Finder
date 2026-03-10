"""
Test script for hybrid search with complex queries.

This script tests the hybrid search system with 10 diverse queries:
- Exact title matches
- Semantic/conceptual queries
- Mood-based queries
- Plot-based queries
- Genre combinations
"""

import requests
import json
import time

# Backend URL
BASE_URL = "http://127.0.0.1:8000"

# Test queries
TEST_QUERIES = [
    {
        "name": "Exact Title Match",
        "query": "inception",
        "description": "Testing exact title matching"
    },
    {
        "name": "Mood-Based Query",
        "query": "something dark and psychological that makes you question reality",
        "description": "Testing semantic understanding of mood and themes"
    },
    {
        "name": "Plot-Based Query",
        "query": "a heist movie with clever twists and ensemble cast",
        "description": "Testing plot element recognition"
    },
    {
        "name": "Genre Combination",
        "query": "sci-fi thriller with time travel or parallel universes",
        "description": "Testing genre and concept combination"
    },
    {
        "name": "Emotional Tone",
        "query": "heartwarming family drama that will make me cry",
        "description": "Testing emotional tone understanding"
    },
    {
        "name": "Setting-Based",
        "query": "dystopian future where society has collapsed",
        "description": "Testing setting and world-building recognition"
    },
    {
        "name": "Character-Driven",
        "query": "strong female protagonist fighting against oppression",
        "description": "Testing character archetype recognition"
    },
    {
        "name": "Specific Title",
        "query": "the dark knight",
        "description": "Testing multi-word exact title match"
    },
    {
        "name": "Abstract Concept",
        "query": "explores the meaning of consciousness and what it means to be human",
        "description": "Testing philosophical theme recognition"
    },
    {
        "name": "Comparative Query",
        "query": "like black mirror but more optimistic about technology",
        "description": "Testing comparative and nuanced understanding"
    }
]


def test_query(query_data):
    """Test a single query and display results."""
    print(f"\n{'='*80}")
    print(f"TEST: {query_data['name']}")
    print(f"Query: \"{query_data['query']}\"")
    print(f"Description: {query_data['description']}")
    print(f"{'='*80}")
    
    try:
        # Make request
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/recommend",
            json={
                "query": query_data['query'],
                "top_k": 5
            },
            timeout=10
        )
        elapsed_time = time.time() - start_time
        
        # Check response
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            query_time = data.get('query_time_ms', 0)
            
            print(f"\n✓ Success! Found {len(results)} results in {query_time:.2f}ms (total: {elapsed_time*1000:.2f}ms)")
            
            if results:
                print(f"\nTop Results:")
                for i, result in enumerate(results, 1):
                    title = result.get('title', 'N/A')
                    score = result.get('similarity_score', 0)
                    media_type = result.get('media_type', 'N/A')
                    description = result.get('description', 'N/A')
                    metadata = result.get('metadata', {})
                    year = metadata.get('year', 'N/A')
                    rating = metadata.get('rating', 'N/A')
                    genre = metadata.get('genre', 'N/A')
                    
                    # Calculate display percentage (same as frontend)
                    display_score = rescale_score(score)
                    
                    print(f"\n  {i}. {title} ({year})")
                    print(f"     Match: {display_score:.0f}% | Type: {media_type} | Genre: {genre} | Rating: {rating}")
                    print(f"     Description: {description[:100]}...")
            else:
                print("\n⚠ No results found")
                
        else:
            print(f"\n✗ Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"\n✗ Error: Request timed out")
    except requests.exceptions.ConnectionError:
        print(f"\n✗ Error: Could not connect to backend at {BASE_URL}")
        print("Make sure the backend is running!")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")


def rescale_score(raw_score):
    """Rescale score to match frontend display (same logic as frontend)."""
    clamped_score = max(0, min(1, raw_score))
    
    if clamped_score >= 0.4:
        normalized = min((clamped_score - 0.4) / 0.3, 1)
        return 70 + normalized * 30
    
    if clamped_score >= 0.3:
        return 60 + ((clamped_score - 0.3) / 0.1) * 10
    
    return (clamped_score / 0.3) * 60


def check_backend_health():
    """Check if backend is running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✓ Backend is healthy at {BASE_URL}")
            return True
        else:
            print(f"✗ Backend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to backend: {str(e)}")
        return False


def main():
    """Run all test queries."""
    print("\n" + "="*80)
    print("HYBRID SEARCH TEST SUITE")
    print("Testing with 10 complex queries")
    print("="*80)
    
    # Check backend health
    if not check_backend_health():
        print("\nPlease start the backend first:")
        print("  cd backend")
        print("  python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000")
        return
    
    # Run all tests
    total_start = time.time()
    for query_data in TEST_QUERIES:
        test_query(query_data)
        time.sleep(0.5)  # Small delay between requests
    
    total_time = time.time() - total_start
    
    # Summary
    print(f"\n{'='*80}")
    print(f"TEST SUITE COMPLETE")
    print(f"Total time: {total_time:.2f}s")
    print(f"Queries tested: {len(TEST_QUERIES)}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
