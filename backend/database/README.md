# Database Module

This module provides the PostgreSQL schema and interface for storing media metadata in the Semantic Media Engine.

## Schema Overview

The database schema includes:

- **media_items table**: Stores metadata for books and TV shows
- **media_type_enum**: ENUM type for 'book' or 'tv_show'
- **Indexes**: Optimized for querying by id, media_type, and metadata fields
- **Triggers**: Automatically updates the `updated_at` timestamp

## Table Structure

### media_items

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key, unique identifier |
| title | VARCHAR(500) | Media title (required) |
| description | TEXT | Plot/synopsis description (required) |
| media_type | media_type_enum | Either 'book' or 'tv_show' |
| metadata | JSONB | Additional metadata (author, genre, year, rating, etc.) |
| created_at | TIMESTAMP | Automatically set on creation |
| updated_at | TIMESTAMP | Automatically updated on modification |

### Indexes

- `idx_media_items_id`: B-tree index on id (primary key)
- `idx_media_items_media_type`: B-tree index on media_type
- `idx_media_items_metadata`: GIN index on metadata (for JSONB queries)
- `idx_media_items_created_at`: B-tree index on created_at

## Setup

### Prerequisites

1. PostgreSQL 12 or higher installed
2. Python environment with dependencies from `requirements.txt`
3. Environment variables configured (see `.env.example`)

### Environment Variables

Create a `.env` file in the `backend` directory:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=semantic_media
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
```

### Running Migrations

To set up the database schema:

```bash
# From the backend directory
cd backend

# Run migration
python database/migrate.py

# Reset schema (drops and recreates)
python database/migrate.py --reset

# Verify schema only
python database/migrate.py --verify
```

## Usage

### Basic Operations

```python
from database import PostgresDatabase

# Initialize database connection
db = PostgresDatabase()

# Insert a media item
media_id = db.insert_media({
    "title": "The Great Gatsby",
    "description": "A classic American novel about the Jazz Age",
    "media_type": "book",
    "metadata": {
        "author": "F. Scott Fitzgerald",
        "genre": "Fiction",
        "year": 1925,
        "rating": 8.5
    }
})

# Retrieve media by IDs
media_items = db.get_media_by_ids([media_id])

# Update media
db.update_media(media_id, {
    "metadata": {
        "author": "F. Scott Fitzgerald",
        "genre": "Classic Fiction",
        "year": 1925,
        "rating": 9.0
    }
})

# Search by metadata
results = db.search_metadata({
    "media_type": "book",
    "genre": "Fiction",
    "min_year": 1920,
    "max_year": 1930
})

# Batch insert
media_ids = db.batch_insert_media([
    {
        "title": "Book 1",
        "description": "Description 1",
        "media_type": "book",
        "metadata": {"author": "Author 1"}
    },
    {
        "title": "Show 1",
        "description": "Description 2",
        "media_type": "tv_show",
        "metadata": {"director": "Director 1"}
    }
])

# Count media items
total_books = db.count_media(media_type="book")
total_items = db.count_media()

# Delete media
db.delete_media(media_id)
```

### Metadata Structure

The `metadata` JSONB field can contain:

**For Books:**
- `author` (string): Book author
- `genre` (string): Genre classification
- `year` (integer): Publication year
- `rating` (float): Average rating (0-10)
- `thumbnail_url` (string): Cover image URL

**For TV Shows:**
- `director` (string): Show director
- `genre` (string): Genre classification
- `year` (integer): Release year
- `rating` (float): Average rating (0-10)
- `seasons` (integer): Number of seasons
- `thumbnail_url` (string): Poster image URL

**Common Fields:**
- `is_latest` (boolean): Flag for new/featured content

## Requirements Validation

This schema satisfies the following requirements:

- **Requirement 10.2**: Validates unique ID for each media item (UUID primary key)
- **Requirement 10.3**: Ensures title is non-empty and at most 500 characters (VARCHAR(500) NOT NULL)
- **Requirement 10.4**: Ensures description is non-empty and at most 5000 characters (TEXT NOT NULL with application-level validation)
- **Requirement 10.5**: Validates media_type is either "book" or "tv_show" (ENUM constraint)

## Performance Considerations

- **GIN Index on metadata**: Enables efficient JSONB queries for filtering by genre, year, rating, etc.
- **B-tree indexes**: Optimize lookups by id and media_type
- **Batch operations**: Use `batch_insert_media()` for bulk inserts to reduce transaction overhead
- **Connection pooling**: Consider using a connection pool (e.g., psycopg2.pool) for production deployments

## Error Handling

The PostgresDatabase class raises:
- `ValueError`: For invalid input data (missing required fields, invalid media_type)
- `psycopg2.Error`: For database operation failures (connection errors, constraint violations)

Always wrap database operations in try-except blocks:

```python
try:
    media_id = db.insert_media(media_data)
except ValueError as e:
    print(f"Invalid data: {e}")
except psycopg2.Error as e:
    print(f"Database error: {e}")
```

## Vector Database (Qdrant)

The `VectorDatabase` class handles embedding storage and similarity search using Qdrant.

### Configuration

The vector database is configured with:
- **Collection name**: `media_embeddings` (configurable)
- **Vector size**: 512 (configurable based on vectorizer)
- **Distance metric**: Cosine similarity (default)
- **Host/Port**: Configurable via environment variables

### Environment Variables

Add to your `.env` file:

```env
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=media_embeddings
```

### Usage

```python
from database import VectorDatabase

# Initialize connection
vector_db = VectorDatabase(
    host="localhost",
    port=6333,
    collection_name="media_embeddings",
    vector_size=512
)

# Insert embedding
vector_db.insert(
    id="media-123",
    vector=[0.1, 0.2, ...],  # 512-dimensional vector
    metadata={"model_version": "v1.0.0"}
)

# Search for similar vectors
results = vector_db.search(
    query_vector=[0.15, 0.25, ...],
    top_k=5
)

# Results format:
# [
#     {"id": "media-123", "score": 0.95, "metadata": {...}},
#     {"id": "media-456", "score": 0.87, "metadata": {...}},
#     ...
# ]

# Search with metadata filters
results = vector_db.search(
    query_vector=[0.15, 0.25, ...],
    top_k=5,
    filter={"model_version": "v1.0.0"}
)

# Delete embedding
vector_db.delete("media-123")

# Get collection count
count = vector_db.count()

# Close connection
vector_db.close()
```

### Features

- **Automatic collection creation**: Creates collection on initialization if it doesn't exist
- **Upsert operations**: Insert or update vectors with the same ID
- **Metadata filtering**: Filter search results by metadata fields
- **Validation**: Validates vector dimensions and finite values
- **Error handling**: Comprehensive error logging and exception handling

### Requirements Validation

This implementation satisfies:

- **Requirement 9.1**: Stores embeddings in Vector DB with corresponding media ID
- **Requirement 9.2**: Ensures each embedding has correct dimensionality
- **Requirement 9.3**: Ensures all vector values are finite floats
- **Requirement 3.2**: Uses cosine similarity as the default metric

## Running Tests

```bash
# Test PostgreSQL operations
pytest tests/test_postgres.py -v

# Test Vector DB operations
pytest tests/test_vector_db.py -v

# Run all database tests
pytest tests/ -v
```
