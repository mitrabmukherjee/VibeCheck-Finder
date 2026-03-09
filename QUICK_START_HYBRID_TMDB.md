# Quick Start: Hybrid Search + TMDB Posters

## 🚀 What You Get

1. **Hybrid Search**: Combines keyword matching (TF-IDF) + semantic understanding (Sentence-BERT)
   - Better at finding exact movie/TV titles
   - Still captures semantic meaning for plot-based queries
   
2. **TMDB Posters**: Beautiful movie/TV show posters automatically fetched
   - Professional images for all media
   - Better visual experience

## ⚡ Quick Setup (3 Steps)

### Step 1: Get TMDB API Key (2 minutes)
1. Go to https://www.themoviedb.org/signup
2. Create free account
3. Go to https://www.themoviedb.org/settings/api
4. Click "Request an API Key" → Choose "Developer"
5. Fill in the form (use any website URL)
6. Copy your API key

### Step 2: Update .env File
Edit `backend/.env` and add your API key:

```env
# Add this line (replace with your actual key)
TMDB_API_KEY=abc123your_actual_key_here

# This should already be set
USE_HYBRID_SEARCH=true
```

### Step 3: Restart Backend
```bash
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Look for these success messages:
```
INFO:     Hybrid Search Engine initialized
INFO:     Hybrid search indexed 6332 items
INFO:     TMDB Service initialized
```

## ✅ Test It

1. Open frontend: http://localhost:3001
2. Search for "Breaking Bad" or "Inception"
3. You should see:
   - Exact title matches ranked first ✓
   - Beautiful poster images ✓
   - Fast search results ✓

## 🎯 Examples

### Before (Sentence-BERT only):
Query: "Breaking Bad"
Results: Similar crime dramas, but title match might not be #1

### After (Hybrid Search):
Query: "Breaking Bad"
Results: "Breaking Bad" is #1, followed by similar shows

### With TMDB:
- Professional posters for all movies/TV shows
- Automatic fallback to gradient if poster not found
- No performance impact

## 🔧 Optional: Test Without Browser

```bash
python test_hybrid_tmdb.py
```

Expected output:
```
✓ Sentence-BERT loaded
✓ Hybrid Search initialized
✓ Indexed 5 items
✓ Hybrid search working correctly!
✓ TMDB service working correctly!
```

## 📊 Performance

- Hybrid search: +10-20ms per query (negligible)
- TMDB API: Async, doesn't block search
- Posters cached after first fetch
- No impact on existing functionality

## 🎨 Customization

### Adjust Search Balance
Edit `backend/main.py` line ~90:

```python
hybrid_search = HybridSearchEngine(
    sbert_vectorizer=ml_engine.sbert_vectorizer,
    tfidf_weight=0.3,  # Keyword matching (0.0-1.0)
    sbert_weight=0.7   # Semantic matching (0.0-1.0)
)
```

- Increase `tfidf_weight` for more exact title matching
- Increase `sbert_weight` for more semantic understanding

### Disable Features
```env
# Disable hybrid search (use Sentence-BERT only)
USE_HYBRID_SEARCH=false

# Disable TMDB posters (remove or comment out)
# TMDB_API_KEY=your_key_here
```

## 🐛 Troubleshooting

### Posters Not Showing?
1. Check TMDB_API_KEY is set correctly in .env
2. Restart backend
3. Check logs for "TMDB Service initialized"
4. Test API key: `curl "https://api.themoviedb.org/3/search/movie?api_key=YOUR_KEY&query=Inception"`

### Hybrid Search Not Working?
1. Check USE_HYBRID_SEARCH=true in .env
2. Restart backend
3. Check logs for "Hybrid Search Engine initialized"

### Import Errors?
```bash
cd backend
pip install requests
```

## 📚 More Info

- Full setup guide: `HYBRID_SEARCH_TMDB_SETUP.md`
- Implementation details: `IMPLEMENTATION_COMPLETE.md`
- Test script: `test_hybrid_tmdb.py`

## 🎉 That's It!

You now have:
- ✅ Better search results (hybrid approach)
- ✅ Beautiful poster images (TMDB)
- ✅ Same fast performance
- ✅ No breaking changes

Enjoy your upgraded search experience!
