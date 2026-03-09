# Sample Data Setup Guide

This guide explains how to set up and run the data pipeline with the sample media dataset for the Semantic Media Engine.

## Overview

The sample dataset (`backend/data/sample_media.csv`) contains 30 media items:
- **15 Books**: Covering genres like Mystery, Fiction, Dystopian, Romance, Thriller, Fantasy, Memoir, Self-Help, Sci-Fi, and Historical Fiction
- **15 TV Shows**: Covering genres like Drama, Sci-Fi, Fantasy, Historical Drama, Comedy, and Mystery

Each item includes:
- Title and rich description (100-300 words)
- Media type (book or tv_show)
- Author/Director information
- Genre classification
- Year of publication/release
- Rating (0-10 scale)
- Additional metadata (seasons for TV shows)

## Prerequisites

Before running the data pipeline, ensure you have:

### 1. PostgreSQL Database Running

```bash
# Check if PostgreSQL is running
psql -U postgres -c "SELECT version();"

# If not running, start it (varies by OS)
# macOS (Homebrew):
brew services start postgresql

# Linux (systemd):
sudo systemctl start postgresql

# Windows:
# Start PostgreSQL service from Services app
```

### 2. Qdrant Vector Database Running

```bash
# Option 1: Run with Docker (recommended)
docker run -p 6333:6333 qdrant/qdrant

# Option 2: Install and run locally
# See https://qdrant.tech/documentation/quick-start/
```

### 3. Environment Variables Configured

Create or update `backend/.env` with:

```bash
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=semantic_media
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333

# CORS Configuration
CORS_ORIGINS=http://localhost:3000
```

### 4. Database Schema Created

Run the migration script to create the required tables:

```bash
cd backend
python database/migrate.py
```

This creates the `media_items` table with the following schema:
- `id` (UUID, primary key)
- `title` (VARCHAR 500)
- `description` (TEXT)
- `media_type` (ENUM: 'book' or 'tv_show')
- `metadata` (JSONB)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

### 5. Python Dependencies Installed

```bash
cd backend
pip install -r requirements.txt
```

## Running the Data Pipeline

### Method 1: Using the Sample Pipeline Script (Recommended)

The `run_sample_pipeline.py` script provides a complete workflow with verification:

```bash
cd backend
python data_pipeline/run_sample_pipeline.py
```

This script will:
1. ✓ Initialize the data pipeline
2. ✓ Load `sample_media.csv` (30 items)
3. ✓ Clean and validate data
4. ✓ Train TF-IDF vectorizer on the corpus
5. ✓ Generate embeddings for all descriptions
6. ✓ Store embeddings in Qdrant Vector DB
7. ✓ Store metadata in PostgreSQL
8. ✓ Verify data consistency between databases
9. ✓ Display statistics and genre distribution

**Expected Output:**

```
================================================================================
SEMANTIC MEDIA ENGINE - SAMPLE DATA PIPELINE
================================================================================

================================================================================
STEP 1: Initializing Data Pipeline
================================================================================
✓ Pipeline initialized successfully

================================================================================
STEP 2: Running Data Pipeline
================================================================================
This will:
  1. Load sample_media.csv
  2. Clean and validate data
  3. Train TF-IDF vectorizer
  4. Generate embeddings
  5. Store embeddings in Qdrant
  6. Store metadata in PostgreSQL

✓ Pipeline execution complete!

================================================================================
STEP 3: Pipeline Statistics
================================================================================
Total loaded:       30 items
Total cleaned:      30 items
Total stored:       30 items
Model version:      v1_20240101_120000
Success rate:       100.0%

================================================================================
STEP 4: Verifying Data Consistency
================================================================================
✓ Data consistency verified: All items have both embeddings and metadata
Embeddings in Vector DB:  30
Metadata in PostgreSQL:   30
Data consistent:          True

================================================================================
STEP 5: Sample Data Overview
================================================================================
Books:              15 items
TV Shows:           15 items

Genre distribution:
  Drama                5 items
  Fiction              4 items
  Sci-Fi               4 items
  Mystery              3 items
  Fantasy              3 items
  Comedy               3 items
  Historical Drama     2 items
  Romance              1 items
  ...

================================================================================
PIPELINE EXECUTION SUMMARY
================================================================================
✓ SUCCESS: All data processed and stored correctly
✓ Embeddings and metadata are consistent
✓ Sample dataset is ready for use

Next steps:
  1. Start the backend server: cd backend && uvicorn main:app --reload
  2. Test the /recommend endpoint with sample queries
  3. Start the frontend: cd frontend && npm run dev

✓ Pipeline closed successfully
```

### Method 2: Using the Example Usage Script

For a simpler execution without verification:

```bash
cd backend
python data_pipeline/example_usage.py
```

### Method 3: Using Python Directly

For custom processing or debugging:

```python
from data_pipeline.data_pipeline import DataPipeline

# Initialize pipeline
pipeline = DataPipeline(
    source_path="backend/data/sample_media.csv",
    vectorizer_path="backend/models",
    embeddings_path="backend/embeddings",
    batch_size=100
)

# Run complete pipeline
stats = pipeline.run(train_vectorizer=True)

print(f"Processed {stats['total_stored']} items")
print(f"Model version: {stats['model_version']}")

# Close connections
pipeline.close()
```

## Verifying the Results

### 1. Check PostgreSQL

```bash
psql -U postgres -d semantic_media

# Count total items
SELECT COUNT(*) FROM media_items;
-- Expected: 30

# Count by type
SELECT media_type, COUNT(*) FROM media_items GROUP BY media_type;
-- Expected: book: 15, tv_show: 15

# View sample items
SELECT id, title, media_type, metadata->>'genre' as genre 
FROM media_items 
LIMIT 5;
```

### 2. Check Qdrant Vector DB

```bash
# Using curl
curl http://localhost:6333/collections/media_embeddings

# Expected response should show:
# - vectors_count: 30
# - status: green
```

### 3. Test the Backend API

Start the backend server:

```bash
cd backend
uvicorn main:app --reload
```

Test the `/recommend` endpoint:

```bash
# Test query for mystery books
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "A thrilling detective mystery with suspense", "top_k": 5}'

# Expected: Should return mystery books like "The Mystery of the Blue Train", "Sherlock", etc.

# Test query for sci-fi shows
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "Space adventures and futuristic technology", "top_k": 5}'

# Expected: Should return sci-fi shows like "Stranger Things", "The Mandalorian", etc.
```

## Sample Queries to Try

Once the pipeline is complete and the backend is running, try these queries:

1. **Mystery/Detective Stories**
   - "A detective solving a murder mystery"
   - "Suspenseful crime investigation"

2. **Science Fiction**
   - "Space exploration and alien encounters"
   - "Time travel and parallel dimensions"

3. **Romance**
   - "Love story set in historical England"
   - "Romantic relationships and social class"

4. **Drama**
   - "Family dysfunction and personal struggles"
   - "Character-driven emotional storytelling"

5. **Fantasy**
   - "Epic battles and magical worlds"
   - "Mythological creatures and ancient legends"

6. **Comedy**
   - "Workplace humor and awkward situations"
   - "Heartwarming comedy with optimistic characters"

## Troubleshooting

### Issue: "Dataset file not found"

**Solution:** Ensure you're running the script from the correct directory:
```bash
cd backend
python data_pipeline/run_sample_pipeline.py
```

### Issue: "Connection refused" (PostgreSQL)

**Solution:** 
1. Check if PostgreSQL is running: `pg_isready`
2. Verify connection parameters in `.env`
3. Ensure database exists: `createdb semantic_media`

### Issue: "Connection refused" (Qdrant)

**Solution:**
1. Check if Qdrant is running: `curl http://localhost:6333/health`
2. Start Qdrant: `docker run -p 6333:6333 qdrant/qdrant`
3. Verify port in `.env` matches Qdrant port

### Issue: "Dataset is empty after cleaning"

**Solution:** This shouldn't happen with the sample dataset. If it does:
1. Check if `sample_media.csv` is corrupted
2. Verify CSV has proper headers and data
3. Re-download or regenerate the sample dataset

### Issue: "Vector size mismatch"

**Solution:** Ensure Qdrant collection vector size matches vectorizer:
```python
# In vector_db_config:
"vector_size": 5000  # Must match vectorizer max_features
```

### Issue: "Model version mismatch"

**Solution:** If you need to retrain the vectorizer:
```bash
# Delete existing model
rm -rf backend/models/vectorizer.pkl

# Run pipeline with train_vectorizer=True
python data_pipeline/run_sample_pipeline.py
```

## Data Consistency

The pipeline ensures data consistency by:

1. **Atomic Operations**: Each batch is processed in a transaction
2. **Verification**: After processing, the script verifies all items have both embeddings and metadata
3. **Error Handling**: If any batch fails, processing halts and rolls back
4. **Logging**: Detailed logs help identify and debug issues

If data inconsistency is detected:
- Check logs for specific errors
- Verify both databases are accessible
- Re-run the pipeline to fix inconsistencies

## Performance

Expected processing times for the sample dataset (30 items):

- **Loading**: < 1 second
- **Cleaning**: < 1 second
- **Vectorizer Training**: 1-2 seconds
- **Embedding Generation**: 1-2 seconds
- **Storage (PostgreSQL)**: < 1 second
- **Storage (Qdrant)**: 1-2 seconds
- **Total**: 5-10 seconds

For larger datasets:
- Use larger batch sizes (1000+)
- Consider parallel processing
- Monitor memory usage

## Next Steps

After successfully running the data pipeline:

1. **Start the Backend Server**
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. **Test the API**
   - Visit http://localhost:8000/docs for interactive API documentation
   - Try sample queries using the `/recommend` endpoint

3. **Start the Frontend**
   ```bash
   cd frontend
   npm run dev
   ```
   - Visit http://localhost:3000
   - Enter natural language queries to get recommendations

4. **Add More Data**
   - Create additional CSV files with more media items
   - Run the pipeline with `train_vectorizer=False` to use existing model
   - Or retrain with `train_vectorizer=True` for better accuracy

## Sample Dataset Details

### Books (15 items)

1. **The Mystery of the Blue Train** - Mystery (1928)
2. **To Kill a Mockingbird** - Fiction (1960)
3. **1984** - Dystopian (1949)
4. **Pride and Prejudice** - Romance (1813)
5. **The Great Gatsby** - Fiction (1925)
6. **The Silent Patient** - Thriller (2019)
7. **Educated** - Memoir (2018)
8. **The Midnight Library** - Fiction (2020)
9. **Where the Crawdads Sing** - Mystery (2018)
10. **The Seven Husbands of Evelyn Hugo** - Historical Fiction (2017)
11. **The Invisible Life of Addie LaRue** - Fantasy (2020)
12. **Atomic Habits** - Self-Help (2018)
13. **Circe** - Fantasy (2018)
14. **Project Hail Mary** - Sci-Fi (2021)
15. **The Song of Achilles** - Historical Fiction (2011)

### TV Shows (15 items)

1. **Breaking Bad** - Drama (2008)
2. **Stranger Things** - Sci-Fi (2016)
3. **The Crown** - Historical Drama (2016)
4. **The Mandalorian** - Sci-Fi (2019)
5. **Game of Thrones** - Fantasy (2011)
6. **The Witcher** - Fantasy (2019)
7. **The Office** - Comedy (2005)
8. **Dark** - Sci-Fi (2017)
9. **Succession** - Drama (2018)
10. **Sherlock** - Mystery (2010)
11. **Chernobyl** - Historical Drama (2019)
12. **The Last of Us** - Drama (2023)
13. **The Bear** - Drama (2022)
14. **Fleabag** - Comedy (2016)
15. **Ted Lasso** - Comedy (2020)

## Requirements Satisfied

This task satisfies the following requirements:

- **7.1**: Load dataset from specified source path ✓
- **7.2**: Validate required columns are present ✓
- **7.3**: Clean and normalize text fields ✓
- **9.4**: Verify embeddings are stored ✓
- **10.1**: Store metadata in PostgreSQL ✓
- **11.4**: Verify total count matches input ✓

## License

Part of the Semantic Media Engine project.
