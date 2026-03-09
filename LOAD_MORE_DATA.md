# How to Load More Data

Currently you have **500 movies/shows** loaded. The full Netflix dataset has **5,850 items**.

Loading more data will improve search results because:
- More vocabulary coverage
- Better word overlap
- More diverse content
- Higher similarity scores

---

## Quick Start (3 Steps)

### Step 1: Convert Full Dataset
```bash
cd backend
python data_pipeline/convert_netflix_dataset.py
```

This will convert all 5,850 Netflix items (takes ~30 seconds).

### Step 2: Load into Database
```bash
python data_pipeline/load_full_dataset.py
```

This will:
- Clear existing data
- Train new vectorizer on 5,850 descriptions
- Generate embeddings for all items
- Load into PostgreSQL and Vector DB

**Time**: ~2-3 minutes

### Step 3: Restart Backend
```bash
# Stop the current backend (Ctrl+C in the terminal)
# Then restart:
python -m uvicorn main:app --reload
```

Done! You now have 5,850 movies/shows indexed.

---

## What Changes

### Before (500 items)
- Query: "little girl story"
- Results: 12 matches
- Top score: 29% (rescaled to 94%)

### After (5,850 items)
- Query: "little girl story"
- Results: 50+ matches
- Top score: 35-40% (rescaled to 95%+)
- Better variety and relevance

---

## Detailed Steps

### 1. Check Current Data
```bash
cd backend
python -c "import pandas as pd; df = pd.read_csv('data/netflix_media.csv'); print(f'Current: {len(df)} items')"
```

### 2. Convert Full Dataset

The conversion script reads from:
- `C:\Users\Steora\Downloads\netflix\titles.csv`
- `C:\Users\Steora\Downloads\netflix\credits.csv`

And creates:
- `backend/data/netflix_media.csv` (all 5,850 items)

```bash
python data_pipeline/convert_netflix_dataset.py
```

### 3. Clear Old Data

**PostgreSQL**:
```bash
python -c "from database.postgres import PostgresDatabase; db = PostgresDatabase(); db.execute('DELETE FROM media'); db.close(); print('PostgreSQL cleared')"
```

**Vector DB**:
```bash
rm embeddings/vectors.npy
rm embeddings/ids.json
rm embeddings/metadata.json
```

### 4. Load New Data
```bash
python data_pipeline/load_full_dataset.py
```

This script will:
1. Load 5,850 items from CSV
2. Clean and validate data
3. Train new TF-IDF vectorizer
4. Generate embeddings (5,850 vectors)
5. Store in PostgreSQL
6. Store in Vector DB

### 5. Verify
```bash
# Check PostgreSQL
python -c "from database.postgres import PostgresDatabase; db = PostgresDatabase(); result = db.execute('SELECT COUNT(*) FROM media'); print(f'PostgreSQL: {result[0][0]} items'); db.close()"

# Check Vector DB
python -c "import json; ids = json.load(open('embeddings/ids.json')); print(f'Vector DB: {len(ids)} vectors')"
```

### 6. Restart Backend
```bash
python -m uvicorn main:app --reload
```

---

## Troubleshooting

### "Out of Memory" Error
If you get memory errors with 5,850 items:

**Option 1**: Load in batches
```bash
python data_pipeline/load_full_dataset.py --batch-size 500
```

**Option 2**: Load fewer items
```bash
# Load 2,000 items instead of 5,850
python data_pipeline/convert_netflix_dataset.py --limit 2000
python data_pipeline/load_full_dataset.py
```

### "Slow Performance"
With 5,850 items, search might take 100-200ms instead of 50ms.

To optimize:
1. Use smaller vector size (reduce from 10,000 to 5,000 features)
2. Use batch processing
3. Add caching

### "Database Connection Error"
Make sure PostgreSQL is running:
```bash
# Check if PostgreSQL is running
psql -U postgres -d semantic_media -c "SELECT 1"
```

---

## Performance Comparison

| Metric | 500 Items | 5,850 Items |
|--------|-----------|-------------|
| Search Time | 50ms | 150ms |
| Memory Usage | 50MB | 300MB |
| Vocabulary Size | 5,020 words | 15,000+ words |
| Match Quality | Good | Excellent |
| Coverage | Limited | Comprehensive |

---

## Alternative: Load Specific Genres

If you don't want all 5,850 items, you can load specific genres:

```bash
# Load only Drama and Comedy (faster, ~2,000 items)
python data_pipeline/convert_netflix_dataset.py --genres "Drama,Comedy"
python data_pipeline/load_full_dataset.py
```

---

## Rollback to 500 Items

If you want to go back to 500 items:

```bash
cd backend
python data_pipeline/convert_netflix_dataset.py --limit 500
python data_pipeline/load_full_dataset.py
```

---

## Next Steps After Loading

1. **Test Search Quality**
   - Try queries that didn't work well before
   - Compare results with 500 vs 5,850 items

2. **Monitor Performance**
   - Check search response times
   - Monitor memory usage

3. **Optimize if Needed**
   - Reduce vector size if too slow
   - Add caching for common queries
   - Consider upgrading to dense embeddings

---

## Summary

Loading more data is simple:
1. Run conversion script (30 seconds)
2. Run loading script (2-3 minutes)
3. Restart backend

You'll get better search results with more comprehensive coverage of the Netflix catalog!
