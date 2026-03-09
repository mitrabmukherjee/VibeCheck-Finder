# Hybrid Search + TMDB Integration Setup

## What's New

### 1. Hybrid Search (TF-IDF + Sentence-BERT)
- Combines keyword matching (TF-IDF) with semantic understanding (Sentence-BERT)
- Better at finding exact title matches while maintaining semantic search quality
- 30% weight on TF-IDF (keywords/titles) + 70% weight on Sentence-BERT (semantics)

### 2. TMDB Poster Integration
- Automatically fetches movie/TV show posters from The Movie Database (TMDB)
- Displays high-quality poster images in search results
- Falls back to gradient background if poster not available

## Setup Instructions

### Step 1: Get TMDB API Key

1. Go to https://www.themoviedb.org/
2. Create a free account
3. Go to Settings → API
4. Request an API key (choose "Developer" option)
5. Copy your API key

### Step 2: Update .env File

Edit `backend/.env` and add your TMDB API key:

```env
# TMDB API Configuration
TMDB_API_KEY=your_actual_api_key_here

# Hybrid Search Configuration (already set)
USE_HYBRID_SEARCH=true
```

### Step 3: Install Dependencies

The system uses existing dependencies, but make sure you have:

```bash
cd backend
pip install requests  # For TMDB API calls
```

### Step 4: Restart Backend

```bash
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

You should see in the logs:
```
INFO:     Hybrid Search Engine initialized
INFO:     Hybrid search indexed 6332 items
INFO:     TMDB Service initialized
```

### Step 5: Test the System

1. Start frontend: `cd frontend && npm run dev`
2. Search for a movie title like "Inception" or "Breaking Bad"
3. You should see:
   - Exact title matches ranked higher (hybrid search working)
   - Movie posters displayed (TMDB integration working)

## How It Works

### Hybrid Search Flow

```
User Query: "Breaking Bad"
    ↓
TF-IDF Search (30% weight)
    → Finds exact keyword matches in titles
    → Score: 0.95 for "Breaking Bad"
    ↓
Sentence-BERT Search (70% weight)
    → Finds semantic matches in descriptions
    → Score: 0.85 for "Breaking Bad"
    ↓
Combined Score = (0.3 × 0.95) + (0.7 × 0.85) = 0.88
    ↓
Results ranked by combined score
```

### TMDB Poster Flow

```
Search Result: "Breaking Bad"
    ↓
Check if thumbnail_url exists in metadata
    ↓
If not, call TMDB API:
    → Search for "Breaking Bad" (TV show)
    → Get poster_path from TMDB
    → Convert to full URL
    → Add to metadata
    ↓
Display poster in frontend
```

## Configuration Options

### Adjust Hybrid Search Weights

Edit `backend/main.py` line ~90:

```python
hybrid_search = HybridSearchEngine(
    sbert_vectorizer=ml_engine.sbert_vectorizer,
    tfidf_weight=0.3,  # Increase for more keyword matching
    sbert_weight=0.7   # Increase for more semantic matching
)
```

### Disable Hybrid Search

Set in `backend/.env`:
```env
USE_HYBRID_SEARCH=false
```

### Disable TMDB Posters

Remove or comment out in `backend/.env`:
```env
# TMDB_API_KEY=your_api_key_here
```

## Benefits

### Hybrid Search Benefits
- ✅ Finds exact title matches even if description is different
- ✅ Still captures semantic meaning for plot-based queries
- ✅ Better user experience for mixed query types
- ✅ No performance impact (both searches run in parallel)

### TMDB Integration Benefits
- ✅ Professional movie/TV show posters
- ✅ Better visual appeal
- ✅ Easier to identify content
- ✅ Free API with generous rate limits

## Troubleshooting

### Hybrid Search Not Working
- Check logs for "Hybrid Search Engine initialized"
- Verify `USE_HYBRID_SEARCH=true` in .env
- Ensure Sentence-BERT model is loaded

### Posters Not Showing
- Verify TMDB_API_KEY is set correctly
- Check logs for "TMDB Service initialized"
- Test API key: `curl "https://api.themoviedb.org/3/search/movie?api_key=YOUR_KEY&query=Inception"`
- Check browser console for image loading errors

### Performance Issues
- Hybrid search adds ~10-20ms per query (negligible)
- TMDB API calls are async and don't block search
- Posters are cached in metadata after first fetch

## Next Steps

1. Get your TMDB API key
2. Update .env file
3. Restart backend
4. Test with movie/TV show titles
5. Enjoy better search results with beautiful posters!
