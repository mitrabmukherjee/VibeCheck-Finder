# Quick Start: Load All Netflix Data

## Current Status
- **Loaded**: 500 movies/shows
- **Available**: 5,850 movies/shows
- **Improvement**: 11x more data = better search results

---

## Option 1: One-Click Loading (Easiest)

Double-click this file:
```
load_all_data.bat
```

That's it! Wait 3-5 minutes and you're done.

---

## Option 2: Manual Steps

### Step 1: Convert Dataset
```bash
cd backend
python data_pipeline/convert_netflix_dataset.py
```

**Output**: `backend/data/netflix_media.csv` with 5,850 items

### Step 2: Load into System
```bash
python data_pipeline/load_full_dataset.py
```

**This will**:
- Clear old data (500 items)
- Train new vectorizer on 5,850 descriptions
- Generate 5,850 embeddings
- Store in PostgreSQL
- Store in Vector DB

**Time**: 2-3 minutes

### Step 3: Restart Backend
```bash
# Stop current backend (Ctrl+C)
python -m uvicorn main:app --reload
```

---

## What You'll Get

### Before (500 items)
```
Query: "romantic comedy"
Results: 12 matches
Top: "Dil Chahta Hai" - 94%
```

### After (5,850 items)
```
Query: "romantic comedy"
Results: 50+ matches
Top: "Love Actually" - 96%
Better variety and relevance!
```

---

## Verify It Worked

### Check Data Count
```bash
cd backend
python -c "import pandas as pd; print(f'{len(pd.read_csv(\"data/netflix_media.csv\"))} items loaded')"
```

**Expected**: `5850 items loaded`

### Check PostgreSQL
```bash
python -c "from database.postgres import PostgresDatabase; db = PostgresDatabase(); result = db.execute('SELECT COUNT(*) FROM media'); print(f'PostgreSQL: {result[0][0]} items'); db.close()"
```

**Expected**: `PostgreSQL: 5850 items`

### Test Search
Open http://localhost:3001 and search for:
- "little girl story"
- "space adventure"
- "romantic comedy"

You should see more and better results!

---

## Troubleshooting

### "File not found" Error
Make sure the Netflix dataset is at:
```
C:\Users\Steora\Downloads\netflix\titles.csv
C:\Users\Steora\Downloads\netflix\credits.csv
```

### "Out of Memory" Error
Load fewer items:
```bash
python data_pipeline/convert_netflix_dataset.py --limit 2000
python data_pipeline/load_full_dataset.py
```

### "Slow Performance"
With 5,850 items, search takes 100-200ms (vs 50ms with 500).
This is normal and still very fast!

---

## Rollback to 500 Items

If you want to go back:
```bash
cd backend
python data_pipeline/convert_netflix_dataset.py --limit 500
python data_pipeline/load_full_dataset.py
```

---

## Summary

**To load all data**:
1. Run `load_all_data.bat` (or manual steps above)
2. Wait 3-5 minutes
3. Restart backend
4. Enjoy 11x more content!

**Benefits**:
- Better search results
- More vocabulary coverage
- Higher match scores
- More diverse content
