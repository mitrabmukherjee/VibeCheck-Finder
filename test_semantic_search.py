"""
Test Sentence-BERT semantic search with various query types.
"""
import requests
import json
from typing import List, Dict

def test_query(query: str, top_k: int = 5) -> Dict:
    """Test a single query and return results."""
    url = "http://127.0.0.1:8000/recommend"
    payload = {"query": query, "top_k": top_k}
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def print_results(query: str, results: Dict):
    """Pretty print search results."""
    print(f"\n{'='*80}")
    print(f"QUERY: '{query}'")
    print(f"{'='*80}")
    
    if "error" in results:
        print(f"❌ ERROR: {results['error']}")
        return
    
    if not results.get("results"):
        print("❌ No results found")
        return
    
    print(f"✅ Found {len(results['results'])} results in {results.get('query_time_ms', 0):.2f}ms\n")
    
    for i, result in enumerate(results["results"], 1):
        score = result["similarity_score"]
        title = result["title"]
        media_type = result["media_type"]
        description = result["description"][:100] + "..." if len(result["description"]) > 100 else result["description"]
        
        print(f"{i}. [{score:.3f}] {title} ({media_type})")
        print(f"   {description}\n")

# Test queries covering different semantic concepts
test_queries = [
    # Children/Family content
    "a little girl",
    "kids show",
    "family friendly movie",
    
    # Genre-based
    "romantic comedy",
    "scary horror movie",
    "action thriller",
    "space adventure",
    
    # Mood/Emotion
    "something funny to watch",
    "sad emotional drama",
    "feel good movie",
    
    # Specific themes
    "high school drama",
    "cooking competition",
    "true crime documentary",
    
    # Abstract concepts
    "finding yourself",
    "overcoming obstacles",
    "friendship and loyalty",
    
    # Synonyms test (should find similar results)
    "young child",  # Similar to "a little girl"
    "frightening film",  # Similar to "scary horror movie"
]

print("🎬 SENTENCE-BERT SEMANTIC SEARCH TEST")
print("=" * 80)
print("Testing various query types to evaluate semantic understanding...")

for query in test_queries:
    results = test_query(query, top_k=5)
    print_results(query, results)

print("\n" + "="*80)
print("✅ TEST COMPLETE")
print("="*80)
