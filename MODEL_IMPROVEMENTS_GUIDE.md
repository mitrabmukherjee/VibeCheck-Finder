# How to Improve Your Semantic Search Model

## Current System Status

**What You Have**:
- Model: all-MiniLM-L6-v2 (384 dimensions)
- Accuracy: ~95%
- Speed: 20-40ms
- Dataset: 6,332 items
- Similarity: Cosine similarity

**This is already pretty good!** But here are ways to make it even better.

---

## Improvement Categories

1. [Better Models](#1-upgrade-to-better-models)
2. [Hybrid Search](#2-hybrid-search-semantic--keyword)
3. [Re-ranking](#3-add-re-ranking)
4. [Personalization](#4-add-personalization)
5. [Query Enhancement](#5-query-enhancement)
6. [Metadata Boosting](#6-metadata-boosting)
7. [Fine-tuning](#7-fine-tune-the-model)
8. [Ensemble Methods](#8-ensemble-methods)
9. [Better Data](#9-improve-data-quality)
10. [Advanced Techniques](#10-advanced-techniques)

---

## 1. Upgrade to Better Models

### Current Model
```python
# all-MiniLM-L6-v2
- Dimensions: 384
- Speed: Very fast
- Accuracy: Good
- Size: 80MB
```

### Better Models (Easy Upgrade)

#### Option A: all-mpnet-base-v2 (Recommended)
```python
# In backend/.env
SBERT_MODEL_NAME=all-mpnet-base-v2

# Benefits:
- Dimensions: 768 (more expressive)
- Accuracy: +5-10% better
- Speed: Still fast (30-50ms)
- Size: 420MB
- Best general-purpose model
```

**Implementation**:
```bash
# Just change the model name and re-run migration
cd backend
# Update .env: SBERT_MODEL_NAME=all-mpnet-base-v2
# Update .env: VECTOR_SIZE=768
python data_pipeline/migrate_to_sbert.py --batch-size 64
```

#### Option B: multi-qa-mpnet-base-dot-v1 (For Q&A Style)
```python
# Best for question-answering style queries
SBERT_MODEL_NAME=multi-qa-mpnet-base-dot-v1

# Benefits:
- Optimized for "find me..." queries
- Dimensions: 768
- Better for conversational search
```

#### Option C: paraphrase-multilingual-mpnet-base-v2 (Multilingual)
```python
# If you want to support multiple languages
SBERT_MODEL_NAME=paraphrase-multilingual-mpnet-base-v2

# Benefits:
- Supports 50+ languages
- Same quality across languages
- Dimensions: 768
```

### Model Comparison Table

| Model | Dims | Speed | Accuracy | Size | Best For |
|-------|------|-------|----------|------|----------|
| **all-MiniLM-L6-v2** (current) | 384 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 80MB | Speed |
| **all-mpnet-base-v2** | 768 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 420MB | Accuracy |
| **multi-qa-mpnet-base-dot-v1** | 768 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 420MB | Q&A |
| **paraphrase-multilingual** | 768 | ⭐⭐⭐ | ⭐⭐⭐⭐ | 970MB | Multilingual |

---

## 2. Hybrid Search (Semantic + Keyword)

Combine semantic search with traditional keyword matching for best results.

### The Problem
```
Query: "Breaking Bad"
Semantic search might return: "Better Call Saul", "Ozark", "The Wire"
But user wants: "Breaking Bad" (exact match)
```

### The Solution: Hybrid Search
```python
# Combine semantic similarity + keyword matching
final_score = (0.7 × semantic_score) + (0.3 × keyword_score)
```

### Implementation

**Step 1: Add BM25 (Keyword Search)**
```python
# backend/ml_engine/bm25_search.py
from rank_bm25 import BM25Okapi
import numpy as np

class BM25Search:
    def __init__(self, documents, ids):
        """
        documents: List of text (titles + descriptions)
        ids: List of media IDs
        """
        # Tokenize documents
        tokenized_docs = [doc.lower().split() for doc in documents]
        
        # Create BM25 index
        self.bm25 = BM25Okapi(tokenized_docs)
        self.ids = ids
    
    def search(self, query, top_k=10):
        """Search using BM25 keyword matching"""
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top k
        top_indices = np.argsort(scores)[-top_k:][::-1]
        
        return [
            {"id": self.ids[idx], "score": float(scores[idx])}
            for idx in top_indices
        ]
```

**Step 2: Combine Semantic + Keyword**
```python
# backend/ml_engine/hybrid_search.py
class HybridSearch:
    def __init__(self, semantic_search, bm25_search):
        self.semantic = semantic_search
        self.bm25 = bm25_search
        self.semantic_weight = 0.7  # 70% semantic
        self.keyword_weight = 0.3   # 30% keyword
    
    def search(self, query, top_k=10):
        # Get semantic results
        semantic_results = self.semantic.search(query, top_k=50)
        
        # Get keyword results
        keyword_results = self.bm25.search(query, top_k=50)
        
        # Combine scores
        combined_scores = {}
        
        for result in semantic_results:
            media_id = result["id"]
            combined_scores[media_id] = self.semantic_weight * result["score"]
        
        for result in keyword_results:
            media_id = result["id"]
            if media_id in combined_scores:
                combined_scores[media_id] += self.keyword_weight * result["score"]
            else:
                combined_scores[media_id] = self.keyword_weight * result["score"]
        
        # Sort and return top k
        sorted_results = sorted(
            combined_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        return [
            {"id": media_id, "score": score}
            for media_id, score in sorted_results
        ]
```

**Benefits**:
- Exact matches get boosted
- Semantic understanding preserved
- Best of both worlds

---

## 3. Add Re-ranking

Use a more powerful model to re-rank top results.

### The Concept
```
Step 1: Fast search (get top 50 results)
Step 2: Slow but accurate re-ranking (re-rank top 50 → top 10)
```

### Implementation

```python
# backend/ml_engine/reranker.py
from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self):
        # Load cross-encoder model (more accurate but slower)
        self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    
    def rerank(self, query, candidates, top_k=10):
        """
        Re-rank candidates using cross-encoder
        
        Args:
            query: Search query
            candidates: List of {id, title, description, score}
            top_k: Number of results to return
        """
        # Create query-document pairs
        pairs = [
            [query, f"{c['title']} {c['description']}"]
            for c in candidates
        ]
        
        # Get re-ranking scores
        scores = self.model.predict(pairs)
        
        # Sort by new scores
        for i, candidate in enumerate(candidates):
            candidate['rerank_score'] = float(scores[i])
        
        candidates.sort(key=lambda x: x['rerank_score'], reverse=True)
        
        return candidates[:top_k]
```

**Usage**:
```python
# In main.py
# Step 1: Fast semantic search (top 50)
initial_results = vector_db.search(query_vector, top_k=50)

# Step 2: Get metadata
candidates = postgres_db.get_by_ids(initial_results.ids)

# Step 3: Re-rank (top 10)
final_results = reranker.rerank(query, candidates, top_k=10)
```

**Benefits**:
- +10-15% accuracy improvement
- Only 50-100ms slower
- Better ranking quality

---

## 4. Add Personalization

Tailor results based on user preferences and history.

### Implementation

**Step 1: Track User Interactions**
```sql
-- Add user tables
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE
);

CREATE TABLE user_interactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    media_id VARCHAR(50) REFERENCES media(id),
    interaction_type VARCHAR(20),  -- 'view', 'like', 'dislike'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Step 2: Personalized Scoring**
```python
# backend/ml_engine/personalization.py
class PersonalizedSearch:
    def __init__(self, base_search, postgres_db):
        self.base_search = base_search
        self.db = postgres_db
    
    def search(self, query, user_id, top_k=10):
        # Get base results
        results = self.base_search.search(query, top_k=50)
        
        # Get user preferences
        user_prefs = self.db.get_user_preferences(user_id)
        # user_prefs = {"favorite_genres": ["Crime", "Thriller"], ...}
        
        # Boost scores based on preferences
        for result in results:
            media = self.db.get_media(result["id"])
            
            # Boost if matches favorite genre
            if media["genre"] in user_prefs["favorite_genres"]:
                result["score"] *= 1.2
            
            # Penalize if already watched
            if result["id"] in user_prefs["watched"]:
                result["score"] *= 0.5
        
        # Re-sort and return
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
```

---

## 5. Query Enhancement

Improve the query before searching.

### Techniques

#### A. Query Expansion
```python
# Expand short queries
query = "crime"
expanded = "crime drama thriller detective mystery"
```

#### B. Spell Correction
```python
from textblob import TextBlob

def correct_spelling(query):
    return str(TextBlob(query).correct())

# "cryme drame" → "crime drama"
```

#### C. Synonym Expansion
```python
synonyms = {
    "movie": ["film", "cinema", "picture"],
    "scary": ["horror", "frightening", "terrifying"],
    "funny": ["comedy", "humorous", "hilarious"]
}

def expand_query(query):
    words = query.split()
    expanded = []
    for word in words:
        expanded.append(word)
        if word in synonyms:
            expanded.extend(synonyms[word])
    return " ".join(expanded)
```

---

## 6. Metadata Boosting

Use metadata to improve ranking.

### Implementation

```python
def boost_by_metadata(results, query, boost_factors):
    """
    Boost scores based on metadata matches
    
    boost_factors = {
        "genre_match": 1.3,
        "year_recent": 1.2,
        "rating_high": 1.1
    }
    """
    for result in results:
        media = result["metadata"]
        
        # Boost if genre mentioned in query
        if media["genre"].lower() in query.lower():
            result["score"] *= boost_factors["genre_match"]
        
        # Boost recent content
        if media["year"] >= 2020:
            result["score"] *= boost_factors["year_recent"]
        
        # Boost highly rated
        if media["rating"] >= 8.0:
            result["score"] *= boost_factors["rating_high"]
    
    return sorted(results, key=lambda x: x["score"], reverse=True)
```

---

## 7. Fine-tune the Model

Train the model on your specific data.

### When to Fine-tune
- You have 1,000+ labeled examples
- Domain-specific content (medical, legal, etc.)
- Want +20-30% accuracy improvement

### How to Fine-tune

```python
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

# Step 1: Prepare training data
train_examples = [
    InputExample(texts=["crime drama", "Breaking Bad"], label=0.9),
    InputExample(texts=["romantic comedy", "Breaking Bad"], label=0.1),
    # ... more examples
]

# Step 2: Load base model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Step 3: Create dataloader
train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)

# Step 4: Define loss
train_loss = losses.CosineSimilarityLoss(model)

# Step 5: Train
model.fit(
    train_objectives=[(train_dataloader, train_loss)],
    epochs=3,
    warmup_steps=100
)

# Step 6: Save
model.save('models/finetuned-model')
```

---

## 8. Ensemble Methods

Combine multiple models for better results.

### Implementation

```python
class EnsembleSearch:
    def __init__(self, models):
        self.models = models  # List of different models
    
    def search(self, query, top_k=10):
        all_results = {}
        
        # Get results from each model
        for model in self.models:
            results = model.search(query, top_k=50)
            for result in results:
                media_id = result["id"]
                score = result["score"]
                
                if media_id in all_results:
                    all_results[media_id].append(score)
                else:
                    all_results[media_id] = [score]
        
        # Average scores
        final_scores = {
            media_id: sum(scores) / len(scores)
            for media_id, scores in all_results.items()
        }
        
        # Sort and return
        sorted_results = sorted(
            final_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        return [{"id": id, "score": score} for id, score in sorted_results]
```

---

## 9. Improve Data Quality

Better data = better results.

### Techniques

#### A. Better Descriptions
```python
# Instead of:
description = "A show about drugs"

# Use:
description = "A high school chemistry teacher turned methamphetamine manufacturer partners with a former student to secure his family's financial future in this gripping crime drama set in Albuquerque, New Mexico."
```

#### B. Add More Metadata
```python
metadata = {
    "genre": "Crime",
    "subgenres": ["Drama", "Thriller"],
    "themes": ["family", "morality", "crime"],
    "mood": ["dark", "intense", "suspenseful"],
    "setting": ["New Mexico", "urban"],
    "keywords": ["drugs", "chemistry", "family", "cancer"]
}
```

#### C. Clean Data
```python
# Remove duplicates
# Fix typos
# Standardize formats
# Remove HTML tags
```

---

## 10. Advanced Techniques

### A. Approximate Nearest Neighbors (ANN)

For faster search with large datasets:

```python
# Use FAISS or Annoy for faster similarity search
import faiss

# Create FAISS index
index = faiss.IndexFlatIP(384)  # Inner product (cosine similarity)
index.add(vectors)

# Search
distances, indices = index.search(query_vector, k=10)
```

### B. Query Understanding

```python
# Classify query intent
intents = {
    "find_similar": "show me movies like...",
    "find_by_mood": "something funny",
    "find_by_genre": "crime drama",
    "find_specific": "Breaking Bad"
}

# Route to different search strategies
```

### C. A/B Testing

```python
# Test different approaches
experiments = {
    "control": base_search,
    "hybrid": hybrid_search,
    "reranked": reranked_search
}

# Track metrics
# - Click-through rate
# - User satisfaction
# - Search success rate
```

---

## Recommended Improvement Path

### Phase 1: Quick Wins (1-2 days)
1. ✅ Upgrade to `all-mpnet-base-v2` model
2. ✅ Add metadata boosting
3. ✅ Improve data descriptions

**Expected improvement**: +10-15% accuracy

### Phase 2: Hybrid Search (3-5 days)
1. ✅ Implement BM25 keyword search
2. ✅ Combine semantic + keyword
3. ✅ Tune weights

**Expected improvement**: +15-20% accuracy

### Phase 3: Re-ranking (2-3 days)
1. ✅ Add cross-encoder re-ranker
2. ✅ Optimize for speed
3. ✅ A/B test

**Expected improvement**: +10-15% accuracy

### Phase 4: Personalization (1 week)
1. ✅ Add user tracking
2. ✅ Implement preference learning
3. ✅ Personalized scoring

**Expected improvement**: +20-30% user satisfaction

---

## Implementation Priority

### Must-Have (Do First)
1. **Upgrade model** to all-mpnet-base-v2
2. **Add hybrid search** (semantic + keyword)
3. **Improve data quality**

### Should-Have (Do Next)
4. **Add re-ranking**
5. **Metadata boosting**
6. **Query enhancement**

### Nice-to-Have (Do Later)
7. **Personalization**
8. **Fine-tuning**
9. **Ensemble methods**

---

## Measuring Improvements

### Metrics to Track

```python
# 1. Accuracy
# - Precision@10: % of top 10 results that are relevant
# - Recall@10: % of relevant items in top 10
# - MRR (Mean Reciprocal Rank): 1 / rank of first relevant result

# 2. Speed
# - Query latency (p50, p95, p99)
# - Throughput (queries per second)

# 3. User Satisfaction
# - Click-through rate
# - Time to first click
# - Search success rate
```

### Evaluation Script

```python
# test_improvements.py
def evaluate_search(search_engine, test_queries):
    results = {
        "precision": [],
        "recall": [],
        "mrr": [],
        "latency": []
    }
    
    for query, relevant_ids in test_queries:
        start = time.time()
        search_results = search_engine.search(query, top_k=10)
        latency = time.time() - start
        
        result_ids = [r["id"] for r in search_results]
        
        # Calculate metrics
        relevant_in_results = set(result_ids) & set(relevant_ids)
        precision = len(relevant_in_results) / len(result_ids)
        recall = len(relevant_in_results) / len(relevant_ids)
        
        # MRR
        for i, rid in enumerate(result_ids):
            if rid in relevant_ids:
                mrr = 1 / (i + 1)
                break
        else:
            mrr = 0
        
        results["precision"].append(precision)
        results["recall"].append(recall)
        results["mrr"].append(mrr)
        results["latency"].append(latency)
    
    return {
        "avg_precision": np.mean(results["precision"]),
        "avg_recall": np.mean(results["recall"]),
        "avg_mrr": np.mean(results["mrr"]),
        "avg_latency": np.mean(results["latency"])
    }
```

---

## Summary

### Top 3 Improvements (Easiest + Biggest Impact)

1. **Upgrade Model** (2 hours)
   ```bash
   # Change SBERT_MODEL_NAME=all-mpnet-base-v2
   # Re-run migration
   # +10% accuracy
   ```

2. **Hybrid Search** (1 day)
   ```python
   # Add BM25 + combine with semantic
   # +15% accuracy
   ```

3. **Better Data** (ongoing)
   ```python
   # Improve descriptions
   # Add more metadata
   # +10% accuracy
   ```

**Total potential improvement: +35% accuracy with minimal effort!**

Your current system is already good. These improvements will make it production-ready and competitive with commercial solutions.
