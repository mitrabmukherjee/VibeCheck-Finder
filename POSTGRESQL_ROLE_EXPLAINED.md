# PostgreSQL's Role in VibeCheck Finder - Detailed Explanation

## Table of Contents
1. [What is PostgreSQL?](#what-is-postgresql)
2. [Why Do We Need PostgreSQL?](#why-do-we-need-postgresql)
3. [What PostgreSQL Stores](#what-postgresql-stores)
4. [Real-World Example](#real-world-example)
5. [PostgreSQL vs Vector Database](#postgresql-vs-vector-database)
6. [Code Examples](#code-examples)
7. [Database Schema](#database-schema)
8. [Query Examples](#query-examples)

---

## What is PostgreSQL?

PostgreSQL is a **relational database** - think of it as an Excel spreadsheet on steroids that can:
- Store millions of rows of data
- Query data super fast
- Handle complex relationships
- Ensure data integrity
- Support concurrent users

In our system, PostgreSQL is like a **library catalog** that stores all the information about movies and TV shows.

---

## Why Do We Need PostgreSQL?

### The Problem
When you search for "a gritty crime drama set in NYC", the system needs to:
1. Find similar content (using AI/vectors) ✅ Vector Database does this
2. Show you the details (title, description, genre, year, rating) ✅ PostgreSQL does this

### The Solution
We use **TWO databases** working together:

```
┌─────────────────────────────────────────────────────────────┐
│                    SEARCH QUERY                              │
│              "a gritty crime drama set in NYC"               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │   STEP 1: Vector Database     │
         │   (Find WHICH shows match)    │
         │                               │
         │   Returns: IDs only           │
         │   ["s1234", "s5678", "s9012"] │
         └───────────────┬───────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │   STEP 2: PostgreSQL          │
         │   (Get DETAILS for those IDs) │
         │                               │
         │   Returns: Full information   │
         │   - Title: "Top Boy"          │
         │   - Description: "..."        │
         │   - Genre: "Crime"            │
         │   - Year: 2019                │
         │   - Rating: 8.4               │
         └───────────────────────────────┘
```

---

## What PostgreSQL Stores

### Actual Data in Our Database

Here's what's stored for each movie/TV show:

```sql
-- Table: media
┌──────────┬─────────────────────┬──────────────────────────┬────────────┬─────────────────────────┐
│    id    │       title         │      description         │ media_type │       metadata          │
├──────────┼─────────────────────┼──────────────────────────┼────────────┼─────────────────────────┤
│ s1234    │ Top Boy             │ Two drug dealers in...   │ tv_show    │ {"genre": "Crime",      │
│          │                     │                          │            │  "year": 2019,          │
│          │                     │                          │            │  "rating": 8.4,         │
│          │                     │                          │            │  "seasons": 4}          │
├──────────┼─────────────────────┼──────────────────────────┼────────────┼─────────────────────────┤
│ s5678    │ Queen Sono          │ A highly trained spy...  │ tv_show    │ {"genre": "Action",     │
│          │                     │                          │            │  "year": 2020,          │
│          │                     │                          │            │  "rating": 7.1,         │
│          │                     │                          │            │  "seasons": 1}          │
├──────────┼─────────────────────┼──────────────────────────┼────────────┼─────────────────────────┤
│ m9012    │ The Godfather       │ The aging patriarch...   │ movie      │ {"genre": "Crime",      │
│          │                     │                          │            │  "year": 1972,          │
│          │                     │                          │            │  "rating": 9.2,         │
│          │                     │                          │            │  "director": "Coppola"} │
└──────────┴─────────────────────┴──────────────────────────┴────────────┴─────────────────────────┘
```

### What Each Column Means

1. **id**: Unique identifier (like a barcode)
   - Example: `s1234`, `m5678`
   - `s` = TV show, `m` = movie

2. **title**: The name of the show/movie
   - Example: "Top Boy", "The Godfather"

3. **description**: Plot summary
   - Example: "Two drug dealers in London navigate..."

4. **media_type**: Is it a movie or TV show?
   - Values: `movie` or `tv_show`

5. **metadata**: Extra information stored as JSON
   - Genre, year, rating, director, cast, etc.
   - Flexible - can add new fields without changing database structure

---

## Real-World Example

Let's walk through a complete search to see PostgreSQL in action:

### Step-by-Step Example

**User Query**: "a gritty crime drama set in NYC"

#### Step 1: Vector Search (NOT PostgreSQL)
```python
# Vector database finds similar content
# Returns only IDs and similarity scores
vector_results = [
    {"id": "s1234", "score": 0.689},  # Top Boy
    {"id": "s5678", "score": 0.665},  # Queen Sono
    {"id": "m9012", "score": 0.621},  # The Godfather
]
```

At this point, we only have IDs. We don't know:
- What are these shows called?
- What are they about?
- What genre are they?
- When were they released?

#### Step 2: PostgreSQL Lookup (THIS IS WHERE POSTGRESQL COMES IN)

```python
# Extract IDs from vector results
media_ids = ["s1234", "s5678", "m9012"]

# Query PostgreSQL for full details
query = """
    SELECT id, title, description, media_type, metadata
    FROM media
    WHERE id IN ('s1234', 's5678', 'm9012')
"""

# PostgreSQL returns full information
postgres_results = [
    {
        "id": "s1234",
        "title": "Top Boy",
        "description": "Two drug dealers in London navigate the dangerous world of organized crime while trying to protect their families.",
        "media_type": "tv_show",
        "metadata": {
            "genre": "Crime",
            "year": 2019,
            "rating": 8.4,
            "seasons": 4,
            "country": "UK"
        }
    },
    {
        "id": "s5678",
        "title": "Queen Sono",
        "description": "A highly trained South African spy must face changing relationships in her personal life while taking on her most dangerous mission yet.",
        "media_type": "tv_show",
        "metadata": {
            "genre": "Action",
            "year": 2020,
            "rating": 7.1,
            "seasons": 1,
            "country": "South Africa"
        }
    },
    {
        "id": "m9012",
        "title": "The Godfather",
        "description": "The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant son.",
        "media_type": "movie",
        "metadata": {
            "genre": "Crime",
            "year": 1972,
            "rating": 9.2,
            "director": "Francis Ford Coppola",
            "runtime": 175
        }
    }
]
```

#### Step 3: Merge Results

```python
# Combine similarity scores with full details
final_results = []
for vector_result in vector_results:
    media_id = vector_result["id"]
    score = vector_result["score"]
    
    # Find matching PostgreSQL data
    postgres_data = find_by_id(postgres_results, media_id)
    
    # Merge them
    final_results.append({
        "id": media_id,
        "title": postgres_data["title"],
        "description": postgres_data["description"],
        "media_type": postgres_data["media_type"],
        "similarity_score": score,
        "metadata": postgres_data["metadata"]
    })
```

#### Step 4: Display to User

```json
{
  "results": [
    {
      "id": "s1234",
      "title": "Top Boy",
      "description": "Two drug dealers in London...",
      "media_type": "tv_show",
      "similarity_score": 0.689,
      "metadata": {
        "genre": "Crime",
        "year": 2019,
        "rating": 8.4
      }
    }
  ],
  "query_time_ms": 23.47
}
```

---

## PostgreSQL vs Vector Database

### Why Not Store Everything in One Database?

| Feature | PostgreSQL | Vector Database |
|---------|-----------|-----------------|
| **Best For** | Structured data (text, numbers, dates) | High-dimensional vectors (embeddings) |
| **Storage** | Rows and columns | Numerical arrays |
| **Search Type** | Exact matches, filters | Similarity search |
| **Example Query** | "Find all movies from 2020" | "Find similar to [0.123, -0.456, ...]" |
| **Speed** | Fast for exact lookups | Fast for similarity |
| **Data Size** | Small (KB per row) | Large (1.5KB per vector) |

### Real Comparison

**PostgreSQL Query**:
```sql
-- Find all crime dramas from 2019
SELECT * FROM media 
WHERE metadata->>'genre' = 'Crime' 
AND metadata->>'year' = '2019';
```
Result: Exact matches only (must have genre="Crime" AND year=2019)

**Vector Database Query**:
```python
# Find content similar to "crime drama"
query_vector = [0.123, -0.456, 0.789, ...]  # 384 numbers
results = vector_db.search(query_vector, top_k=10)
```
Result: Semantically similar content (might include thrillers, detective shows, etc.)

---

## Code Examples

### How We Use PostgreSQL in Our Code

#### 1. Database Connection (postgres.py)

```python
import psycopg2
from psycopg2.extras import RealDictCursor

class PostgresDatabase:
    def __init__(self):
        # Connect to PostgreSQL
        self.conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="semantic_media",
            user="postgres",
            password="root24"
        )
    
    def get_media_by_ids(self, media_ids):
        """
        Fetch full details for a list of media IDs
        
        Args:
            media_ids: List of IDs like ["s1234", "s5678"]
        
        Returns:
            List of dictionaries with full media details
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        # SQL query with placeholders
        query = """
            SELECT id, title, description, media_type, metadata
            FROM media
            WHERE id = ANY(%s)
        """
        
        # Execute query
        cursor.execute(query, (media_ids,))
        
        # Fetch results
        results = cursor.fetchall()
        
        return results
```

#### 2. Using PostgreSQL in the API (main.py)

```python
@app.post("/recommend")
async def recommend(request: RecommendationRequest):
    # Step 1: Vector search (get IDs)
    query_vector = ml_engine.vectorize_query(request.query)
    search_results = vector_db.search(query_vector, top_k=12)
    
    # search_results = [
    #     {"id": "s1234", "score": 0.689},
    #     {"id": "s5678", "score": 0.665},
    #     ...
    # ]
    
    # Step 2: Get IDs from vector results
    media_ids = [result["id"] for result in search_results]
    # media_ids = ["s1234", "s5678", ...]
    
    # Step 3: Query PostgreSQL for full details
    media_objects = postgres_db.get_media_by_ids(media_ids)
    
    # media_objects = [
    #     {
    #         "id": "s1234",
    #         "title": "Top Boy",
    #         "description": "...",
    #         "media_type": "tv_show",
    #         "metadata": {"genre": "Crime", "year": 2019, ...}
    #     },
    #     ...
    # ]
    
    # Step 4: Merge scores with metadata
    recommendations = []
    for result in search_results:
        media_id = result["id"]
        score = result["score"]
        
        # Find matching media object
        media = next(m for m in media_objects if m["id"] == media_id)
        
        # Create recommendation
        recommendations.append({
            "id": media_id,
            "title": media["title"],
            "description": media["description"],
            "media_type": media["media_type"],
            "similarity_score": score,
            "metadata": media["metadata"]
        })
    
    return {"results": recommendations}
```

---

## Database Schema

### Complete Schema Definition

```sql
-- Create the media table
CREATE TABLE media (
    -- Primary key: unique identifier
    id VARCHAR(50) PRIMARY KEY,
    
    -- Basic information
    title VARCHAR(500) NOT NULL,
    description TEXT,
    media_type VARCHAR(20) NOT NULL CHECK (media_type IN ('movie', 'tv_show')),
    
    -- Flexible metadata as JSON
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast queries
CREATE INDEX idx_media_type ON media(media_type);
CREATE INDEX idx_metadata_genre ON media USING GIN ((metadata->'genre'));
CREATE INDEX idx_metadata_year ON media USING GIN ((metadata->'year'));
CREATE INDEX idx_title ON media(title);

-- Example: Insert a movie
INSERT INTO media (id, title, description, media_type, metadata) VALUES (
    'm1',
    'The Godfather',
    'The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant son.',
    'movie',
    '{"genre": "Crime", "year": 1972, "rating": 9.2, "director": "Francis Ford Coppola", "runtime": 175}'
);

-- Example: Insert a TV show
INSERT INTO media (id, title, description, media_type, metadata) VALUES (
    's1',
    'Top Boy',
    'Two drug dealers in London navigate the dangerous world of organized crime.',
    'tv_show',
    '{"genre": "Crime", "year": 2019, "rating": 8.4, "seasons": 4, "country": "UK"}'
);
```

---

## Query Examples

### Common PostgreSQL Queries in Our System

#### 1. Get Media by IDs (Most Common)
```sql
-- Used after vector search to get full details
SELECT id, title, description, media_type, metadata
FROM media
WHERE id IN ('s1234', 's5678', 'm9012');
```

#### 2. Get All Movies
```sql
SELECT * FROM media
WHERE media_type = 'movie';
```

#### 3. Get Crime Dramas from 2019
```sql
SELECT * FROM media
WHERE metadata->>'genre' = 'Crime'
AND metadata->>'year' = '2019';
```

#### 4. Get Highly Rated Content (Rating > 8.0)
```sql
SELECT * FROM media
WHERE CAST(metadata->>'rating' AS FLOAT) > 8.0
ORDER BY CAST(metadata->>'rating' AS FLOAT) DESC;
```

#### 5. Search by Title (Partial Match)
```sql
SELECT * FROM media
WHERE title ILIKE '%godfather%';
```

#### 6. Count Movies vs TV Shows
```sql
SELECT media_type, COUNT(*) as count
FROM media
GROUP BY media_type;

-- Result:
-- media_type | count
-- -----------+-------
-- movie      | 2841
-- tv_show    | 3491
```

---

## Summary

### PostgreSQL's Role in 3 Points

1. **Storage**: Stores all the human-readable information about movies/TV shows
   - Titles, descriptions, genres, years, ratings, etc.

2. **Retrieval**: Quickly fetches details for specific IDs
   - Vector database says "these IDs match"
   - PostgreSQL says "here's what those IDs are"

3. **Filtering**: Allows filtering by metadata
   - Genre, year, rating, media type, etc.

### The Perfect Partnership

```
Vector Database: "I found content similar to your search!"
                 ↓
                 Returns: IDs + similarity scores
                 ↓
PostgreSQL:      "Here's what those IDs actually are!"
                 ↓
                 Returns: Titles, descriptions, metadata
                 ↓
User:            "Perfect! Show me Top Boy!"
```

Without PostgreSQL, you'd only see:
- "Result 1: ID s1234, Score: 0.689"
- "Result 2: ID s5678, Score: 0.665"

With PostgreSQL, you see:
- "Top Boy (2019) - Crime Drama - ⭐ 8.4"
- "Queen Sono (2020) - Action Thriller - ⭐ 7.1"

**PostgreSQL makes the search results human-readable and useful!**
