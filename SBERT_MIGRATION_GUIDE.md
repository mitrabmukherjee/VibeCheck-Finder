# Sentence-BERT Migration Guide

This guide provides step-by-step instructions for migrating the VibeCheck Finder semantic search system from TF-IDF vectorization to Sentence-BERT dense embeddings.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Migration Steps](#migration-steps)
4. [Validation](#validation)
5. [Rollback Procedure](#rollback-procedure)
6. [Troubleshooting](#troubleshooting)

## Overview

The Sentence-BERT upgrade replaces TF-IDF sparse vectors (~5000 dimensions) with dense semantic embeddings (384 dimensions). This enables true semantic understanding of search queries, allowing the system to match conceptually similar terms rather than relying solely on exact word overlap.

**Key Changes:**
- **Vector Dimensionality**: 5000 → 384 dimensions
- **Similarity Scores**: 15-30% → 60-80% for good matches
- **Semantic Understanding**: Understands that "little girl" ≈ "young girl" ≈ "small child"
- **Model**: TF-IDF → Sentence-BERT (all-MiniLM-L6-v2)

## Prerequisites

Before starting the migration, ensure you have:

1. **Python Dependencies**: Install sentence-transformers library
   ```bash
   pip install sentence-transformers>=2.0.0
   ```

2. **Backup**: Create a backup of your current system
   ```bash
   # Backup embeddings
   cp -r backend/embeddings backend/embeddings_backup_$(date +%Y%m%d_%H%M%S)
   
   # Backup environment configuration
   cp backend/.env backend/.env.backup
   ```

3. **Disk Space**: Ensure sufficient disk space for:
   - Sentence-BERT model weights (~90 MB)
   - New embeddings (384 dimensions × 5,832 items × 4 bytes ≈ 9 MB)
   - Backup of old embeddings

4. **Database Access**: Verify PostgreSQL is running and accessible
   ```bash
   psql -h localhost -U postgres -d semantic_media -c "SELECT COUNT(*) FROM media;"
   ```

5. **Existing Data**: Ensure you have media items loaded in PostgreSQL
   - Minimum: 100 items for testing
   - Full dataset: 5,832 Netflix items

## Migration Steps

### Step 1: Update Environment Configuration

1. Open `backend/.env` file

2. Update the following variables:
   ```bash
   # Change vectorizer type from tfidf to sbert
   VECTORIZER_TYPE=sbert
   
   # Set Sentence-BERT model name
   SBERT_MODEL_NAME=all-MiniLM-L6-v2
   
   # Update vector size to match Sentence-BERT dimensions
   VECTOR_SIZE=384
   
   # Ensure file-based storage is enabled
   USE_FILE_STORAGE=true
   
   # Verify paths
   VECTORIZER_PATH=backend/models
   EMBEDDINGS_PATH=backend/embeddings
   ```

3. Save the file

### Step 2: Run Migration Script

The migration script will:
- Load all media items from PostgreSQL
- Generate Sentence-BERT embeddings in batches
- Store embeddings in the file-based vector database
- Create a backup of existing TF-IDF embeddings
- Generate a migration report

**Basic Migration (with backup):**
```bash
cd backend
python data_pipeline/migrate_to_sbert.py
```

**Migration Options:**

```bash
# Dry run (validate without writing)
python data_pipeline/migrate_to_sbert.py --dry-run

# Custom batch size (default: 32)
python data_pipeline/migrate_to_sbert.py --batch-size 64

# Skip backup (not recommended)
python data_pipeline/migrate_to_sbert.py --no-backup

# Custom storage path
python data_pipeline/migrate_to_sbert.py --storage-path /path/to/embeddings

# Specify PostgreSQL connection
python data_pipeline/migrate_to_sbert.py --postgres-host localhost --postgres-port 5432
```

**Expected Output:**
```
Starting Sentence-BERT Migration
================================
Storage path: backend/embeddings
Backup: True
Dry run: False

Initializing Sentence-BERT vectorizer...
Model: all-MiniLM-L6-v2
Embedding dimension: 384

Creating backup...
Backup created: backend/embeddings/backup_20240115_103000

Loading media items from PostgreSQL...
Loaded 5832 media items

Generating embeddings...
Progress: 100%|████████████████████| 5832/5832 [00:45<00:00, 129.38it/s]

Storing embeddings in vector database...
Stored 5832 embeddings

Migration Summary
=================
Status: completed
Total items: 5832
Successful: 5832
Failed: 0
Duration: 45.2 seconds
Backup location: backend/embeddings/backup_20240115_103000

Migration completed successfully!
```

### Step 3: Validate Migration

Run the validation script to verify embedding quality:

```bash
cd backend
python data_pipeline/validate_sbert.py
```

**Validation Checks:**
1. ✓ All embeddings have exactly 384 dimensions
2. ✓ All embedding values are finite (no NaN or infinity)
3. ✓ Encoding is idempotent (same input → same output)
4. ✓ Semantic understanding tests pass
5. ✓ Similarity scores are in expected range (60-80%)

**Save Validation Report:**
```bash
python data_pipeline/validate_sbert.py --output validation_report.json
```

**Compare with TF-IDF:**
```bash
# This will compare search results between TF-IDF and Sentence-BERT
python data_pipeline/validate_sbert.py --compare-tfidf
```

### Step 4: Restart Backend Server

1. Stop the current backend server (Ctrl+C)

2. Restart with new configuration:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

3. Verify startup logs show Sentence-BERT initialization:
   ```
   INFO:     ML Engine initialized with vectorizer_type=sbert
   INFO:     Sentence-BERT model: all-MiniLM-L6-v2
   INFO:     File-based Vector Database initialized (vector_size=384)
   INFO:     Loaded 5832 embeddings
   ```

### Step 5: Test Search Functionality

Test the API with example queries:

```bash
# Test semantic understanding
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "little girl", "top_k": 5}'

# Expected: High similarity scores (60-80%) for content about young girls, children

curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "romantic comedy", "top_k": 5}'

# Expected: High similarity scores for love stories with humor

curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "space adventure", "top_k": 5}'

# Expected: High similarity scores for sci-fi exploration content
```

**Verify Response Format:**
- Results should be sorted by similarity_score (descending)
- Scores should be in range 0.0 to 1.0
- Response should include query_time_ms
- All metadata fields should be present

## Validation

### Automated Validation

Run the comprehensive validation script:

```bash
python backend/data_pipeline/validate_sbert.py --output validation_report.json
```

### Manual Validation Checklist

- [ ] All 5,832 embeddings migrated successfully
- [ ] Embedding dimensions are 384 (not 5000)
- [ ] Search queries return results
- [ ] Similarity scores are higher than TF-IDF (60-80% vs 15-30%)
- [ ] Semantic queries work (e.g., "little girl" finds "young girl" content)
- [ ] API response format unchanged (backward compatible)
- [ ] Query processing time < 200ms
- [ ] No errors in backend logs
- [ ] Frontend still works without changes

### Performance Validation

Test search performance:

```bash
# Run multiple queries and measure average response time
for i in {1..10}; do
  curl -X POST http://localhost:8000/recommend \
    -H "Content-Type: application/json" \
    -d '{"query": "mystery detective", "top_k": 5}' \
    -w "\nTime: %{time_total}s\n"
done
```

**Expected Performance:**
- Query encoding: < 50ms
- Vector search: < 100ms
- Total response time: < 200ms

## Rollback Procedure

If you encounter issues and need to rollback to TF-IDF:

### Option 1: Automatic Rollback (if backup exists)

```bash
cd backend
python data_pipeline/migrate_to_sbert.py --rollback
```

This will:
1. Restore TF-IDF embeddings from backup
2. Update vector database configuration
3. Verify restoration

### Option 2: Manual Rollback

1. **Stop the backend server** (Ctrl+C)

2. **Restore embeddings from backup:**
   ```bash
   # Find your backup directory
   ls -la backend/embeddings/backup_*
   
   # Restore from backup (replace timestamp with your backup)
   cp backend/embeddings/backup_20240115_103000/* backend/embeddings/
   ```

3. **Update environment configuration:**
   ```bash
   # Edit backend/.env
   VECTORIZER_TYPE=tfidf
   VECTOR_SIZE=5000
   ```

4. **Restart backend server:**
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

5. **Verify TF-IDF is active:**
   ```
   INFO:     ML Engine initialized with vectorizer_type=tfidf
   INFO:     File-based Vector Database initialized (vector_size=5000)
   ```

6. **Test search functionality:**
   ```bash
   curl -X POST http://localhost:8000/recommend \
     -H "Content-Type: application/json" \
     -d '{"query": "mystery novel", "top_k": 5}'
   ```

## Troubleshooting

### Issue: Model Download Fails

**Symptoms:**
```
Error: Failed to download model from HuggingFace
```

**Solutions:**
1. Check internet connection
2. Verify HuggingFace is accessible
3. Try manual download:
   ```bash
   python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
   ```
4. Use cached model if available:
   ```bash
   # Check cache location
   ls -la ~/.cache/torch/sentence_transformers/
   ```

### Issue: Out of Memory During Migration

**Symptoms:**
```
MemoryError: Unable to allocate array
```

**Solutions:**
1. Reduce batch size:
   ```bash
   python data_pipeline/migrate_to_sbert.py --batch-size 16
   ```
2. Close other applications
3. Increase system swap space
4. Use CPU instead of GPU (automatic fallback)

### Issue: Vector Size Mismatch

**Symptoms:**
```
ValueError: Vector size mismatch: provided vector has 384 dimensions, but database is configured for 5000 dimensions
```

**Solutions:**
1. Verify VECTOR_SIZE in .env matches VECTORIZER_TYPE:
   - VECTORIZER_TYPE=sbert → VECTOR_SIZE=384
   - VECTORIZER_TYPE=tfidf → VECTOR_SIZE=5000
2. Clear old embeddings:
   ```bash
   rm backend/embeddings/vectors.npy
   rm backend/embeddings/metadata.json
   rm backend/embeddings/ids.json
   ```
3. Re-run migration

### Issue: Low Similarity Scores

**Symptoms:**
- Similarity scores still in 15-30% range (like TF-IDF)
- Semantic queries don't work well

**Solutions:**
1. Verify Sentence-BERT is active:
   ```bash
   # Check backend logs for:
   # "ML Engine initialized with vectorizer_type=sbert"
   ```
2. Verify embeddings are 384 dimensions:
   ```bash
   python -c "import numpy as np; v = np.load('backend/embeddings/vectors.npy'); print(v.shape)"
   # Should print: (5832, 384)
   ```
3. Re-run migration if dimensions are wrong

### Issue: API Returns 503 Service Unavailable

**Symptoms:**
```json
{
  "error": 503,
  "message": "Search service temporarily unavailable. Please try again in a few moments."
}
```

**Solutions:**
1. Check backend logs for errors
2. Verify model loaded successfully:
   ```bash
   # Look for "ML Engine initialized" in logs
   ```
3. Verify embeddings exist:
   ```bash
   ls -la backend/embeddings/
   # Should see: vectors.npy, metadata.json, ids.json
   ```
4. Restart backend server

### Issue: Migration Script Hangs

**Symptoms:**
- Script appears frozen during "Generating embeddings..."
- No progress for several minutes

**Solutions:**
1. Check if model is downloading (first run only):
   ```bash
   # Monitor network activity
   # Model download is ~90 MB, may take time on slow connections
   ```
2. Enable progress bar:
   ```bash
   python data_pipeline/migrate_to_sbert.py --show-progress
   ```
3. Check system resources (CPU, memory)
4. Try smaller batch size

### Issue: Backup Not Created

**Symptoms:**
```
Warning: Backup creation failed
```

**Solutions:**
1. Check disk space:
   ```bash
   df -h backend/embeddings
   ```
2. Check write permissions:
   ```bash
   ls -la backend/embeddings
   ```
3. Create backup manually:
   ```bash
   mkdir -p backend/embeddings/backup_manual
   cp backend/embeddings/*.npy backend/embeddings/backup_manual/
   cp backend/embeddings/*.json backend/embeddings/backup_manual/
   ```

## Additional Resources

- **Sentence-BERT Documentation**: https://www.sbert.net/
- **Model Card**: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- **Validation Script**: `backend/data_pipeline/validate_sbert.py`
- **Migration Script**: `backend/data_pipeline/migrate_to_sbert.py`
- **Design Document**: `.kiro/specs/sentence-bert-upgrade/design.md`
- **Requirements**: `.kiro/specs/sentence-bert-upgrade/requirements.md`

## Support

If you encounter issues not covered in this guide:

1. Check backend logs for detailed error messages
2. Run validation script to identify specific problems
3. Review the design document for technical details
4. Check GitHub issues for similar problems
5. Create a new issue with:
   - Error messages from logs
   - Validation report output
   - System information (OS, Python version, available memory)
   - Steps to reproduce the issue
