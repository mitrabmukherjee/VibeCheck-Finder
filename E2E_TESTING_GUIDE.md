# End-to-End Testing Guide
## Semantic Media Engine

This guide provides comprehensive instructions for testing the complete end-to-end flow of the Semantic Media Engine, from frontend query submission to backend recommendation retrieval.

## Overview

The E2E testing process verifies that:
- Backend server starts successfully and serves the API
- Frontend development server starts and connects to the backend
- User queries are processed correctly through the entire stack
- Recommendations are returned with proper formatting and scores
- Various query types (books, TV shows, genres) work as expected
- Error handling works correctly for edge cases

## Prerequisites

Before running E2E tests, ensure:

1. **PostgreSQL is running** with the `semantic_media` database created
2. **Qdrant vector database is running** (via Docker or local installation)
3. **Sample data has been loaded** using the data pipeline
4. **Environment variables are configured** in both backend and frontend

### Quick Prerequisites Check

```bash
# Check PostgreSQL
pg_isready -h localhost -p 5432

# Check Qdrant
curl http://localhost:6333/health

# Verify sample data exists
psql -d semantic_media -c "SELECT COUNT(*) FROM media_items;"
```

## Test Setup

### 1. Start Backend Server

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     ML Engine initialized
INFO:     PostgreSQL connection initialized
INFO:     Vector Database initialized
INFO:     Application startup complete.
```

**Verification:**
- Open http://localhost:8000 in browser - should see `{"message": "Semantic Media Engine API"}`
- Open http://localhost:8000/docs - should see Swagger API documentation
- Check http://localhost:8000/health - should return `{"status": "healthy"}`

### 2. Start Frontend Development Server

In a new terminal:

```bash
cd frontend
npm run dev
```

**Expected Output:**
```
> frontend@0.1.0 dev
> next dev

  ▲ Next.js 14.x.x
  - Local:        http://localhost:3000
  - Network:      http://192.168.x.x:3000

 ✓ Ready in 2.5s
```

**Verification:**
- Open http://localhost:3000 in browser
- Should see the Semantic Media Engine search interface
- Input field should be visible with placeholder text
- No console errors in browser DevTools

## Manual E2E Test Cases

### Test Case 1: Basic Book Query

**Objective:** Verify that a simple book query returns relevant recommendations.

**Steps:**
1. Navigate to http://localhost:3000
2. Enter query: `mystery book with detective`
3. Wait for results to load (should see loading spinner)
4. Verify recommendations appear

**Expected Results:**
- Loading indicator appears immediately
- Results load within 2-3 seconds
- At least 3-5 book recommendations displayed
- Each result shows:
  - Title
  - Description
  - Media type badge (📚 Book)
  - Similarity score (percentage)
  - Metadata (author, genre, year, rating)
- Results are sorted by similarity score (highest first)
- Top result should be a mystery/detective book (e.g., "The Mystery of the Blue Train", "Sherlock")

**Sample Expected Result:**
```
The Mystery of the Blue Train
A classic Agatha Christie mystery featuring Hercule Poirot...
📚 Book | Mystery | 1928 | by Agatha Christie | ⭐ 8.5/10
85.3% match
```

### Test Case 2: TV Show Query

**Objective:** Verify that TV show queries work correctly.

**Steps:**
1. Clear previous query
2. Enter query: `science fiction show about time travel`
3. Wait for results

**Expected Results:**
- Results include TV shows (📺 TV Show badge)
- Top results should be sci-fi shows (e.g., "Dark", "Stranger Things")
- Metadata includes director, seasons, genre
- Similarity scores reflect relevance to "time travel" and "science fiction"

**Sample Expected Result:**
```
Dark
A German science fiction thriller that begins with a child's disappearance...
📺 TV Show | Sci-Fi | 2017 | dir. Baran bo Odar | ⭐ 8.8/10 | 3 seasons
92.1% match
```

### Test Case 3: Genre-Specific Query

**Objective:** Test queries targeting specific genres.

**Steps:**
1. Enter query: `romantic period drama`
2. Wait for results

**Expected Results:**
- Results include romance/historical content
- Books like "Pride and Prejudice" should rank highly
- TV shows like "The Crown" may appear
- Similarity scores reflect genre matching

### Test Case 4: Mood-Based Query

**Objective:** Test natural language mood/atmosphere queries.

**Steps:**
1. Enter query: `dark psychological thriller`
2. Wait for results

**Expected Results:**
- Results include thrillers and psychological content
- Books like "The Silent Patient" should appear
- TV shows like "Breaking Bad" may appear
- Descriptions emphasize dark/psychological themes

### Test Case 5: Empty Results

**Objective:** Verify handling of queries with no matches.

**Steps:**
1. Enter query: `quantum physics textbook for advanced mathematics`
2. Wait for results

**Expected Results:**
- Loading indicator appears and disappears
- "No recommendations found" message displays
- Suggestion to "Try a different search query"
- No error messages or crashes

### Test Case 6: Short Query Handling

**Objective:** Test minimum query length validation.

**Steps:**
1. Enter query: `ab` (2 characters)
2. Observe behavior

**Expected Results:**
- No API request is made (check Network tab)
- Helper text shows: "Enter at least 3 characters to search"
- No loading indicator
- No results displayed

### Test Case 7: Long Query Handling

**Objective:** Test query length limits.

**Steps:**
1. Enter a very long query (500+ characters)
2. Wait for results

**Expected Results:**
- Query is accepted (backend limit is 1000 characters)
- Results are returned normally
- No errors or truncation issues

### Test Case 8: Special Characters

**Objective:** Test query preprocessing with special characters.

**Steps:**
1. Enter query: `mystery!!! with @detective #crime`
2. Wait for results

**Expected Results:**
- Special characters are handled gracefully
- Results are similar to "mystery detective crime"
- No errors or crashes

### Test Case 9: Debouncing Behavior

**Objective:** Verify input debouncing works correctly.

**Steps:**
1. Type quickly: `s` `c` `i` `f` `i` (one character at a time, rapidly)
2. Observe network requests in DevTools

**Expected Results:**
- Only ONE API request is made after typing stops
- Request is delayed by ~500ms after last keystroke
- No multiple simultaneous requests

### Test Case 10: Error Handling - Backend Down

**Objective:** Test frontend error handling when backend is unavailable.

**Steps:**
1. Stop the backend server (Ctrl+C)
2. Enter query: `mystery book`
3. Wait for response

**Expected Results:**
- Loading indicator appears
- After timeout, error message displays in red box
- Error message is user-friendly (e.g., "Failed to fetch recommendations")
- No console errors that crash the app
- User can retry after backend restarts

## Automated E2E Test Script

For automated testing, use the provided test script:

```bash
# Run automated E2E tests
python test_e2e.py
```

See `test_e2e.py` for implementation details.

## Performance Benchmarks

Expected performance metrics:

| Metric | Target | Acceptable Range |
|--------|--------|------------------|
| Query processing time | < 100ms | 50-200ms |
| Total response time | < 500ms | 200-1000ms |
| Frontend render time | < 100ms | 50-300ms |
| End-to-end latency | < 1s | 0.5-2s |

**Measuring Performance:**

1. Check `query_time_ms` in API response (visible in Network tab)
2. Use browser DevTools Performance tab
3. Monitor backend logs for processing times

## Common Issues and Troubleshooting

### Issue: CORS Errors

**Symptoms:**
- Console error: `Access to fetch at 'http://localhost:8000/recommend' from origin 'http://localhost:3000' has been blocked by CORS policy`

**Solution:**
1. Check `CORS_ORIGINS` in `backend/.env` includes `http://localhost:3000`
2. Restart backend server after changing `.env`
3. Clear browser cache

### Issue: No Results Returned

**Symptoms:**
- Query completes but shows "No recommendations found"
- All queries return empty results

**Solution:**
1. Verify sample data is loaded: `psql -d semantic_media -c "SELECT COUNT(*) FROM media_items;"`
2. Check Qdrant has embeddings: `curl http://localhost:6333/collections/media_embeddings`
3. Verify vectorizer model exists: `ls backend/models/vectorizer.pkl`
4. Re-run data pipeline if needed

### Issue: Backend Startup Fails

**Symptoms:**
- Backend crashes on startup
- Error: "ML Engine not initialized" or "Database service unavailable"

**Solution:**
1. Check PostgreSQL is running: `pg_isready`
2. Check Qdrant is running: `curl http://localhost:6333/health`
3. Verify `.env` configuration
4. Check backend logs for specific error messages

### Issue: Slow Response Times

**Symptoms:**
- Queries take > 2 seconds to return results
- Loading indicator visible for extended periods

**Solution:**
1. Check database connection latency
2. Verify Qdrant is running locally (not remote)
3. Ensure vectorizer model is loaded (not re-training each time)
4. Check system resources (CPU, memory)

### Issue: Frontend Not Connecting to Backend

**Symptoms:**
- Network errors in console
- "Failed to fetch" errors

**Solution:**
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
3. Ensure no firewall blocking port 8000
4. Try `http://127.0.0.1:8000` instead of `localhost`

## Test Data Validation

### Verify Sample Data Quality

```bash
# Check total media items
psql -d semantic_media -c "SELECT COUNT(*) FROM media_items;"

# Check media type distribution
psql -d semantic_media -c "SELECT media_type, COUNT(*) FROM media_items GROUP BY media_type;"

# Check for items with missing metadata
psql -d semantic_media -c "SELECT COUNT(*) FROM media_items WHERE metadata IS NULL;"

# Verify embeddings in Qdrant
curl http://localhost:6333/collections/media_embeddings
```

**Expected Results:**
- At least 20-30 media items in PostgreSQL
- Roughly equal distribution of books and TV shows
- No NULL metadata fields
- Qdrant collection exists with matching vector count

## Test Query Examples

### Books

| Query | Expected Top Results |
|-------|---------------------|
| `mystery detective investigation` | The Mystery of the Blue Train, Sherlock, The Silent Patient |
| `romantic love story` | Pride and Prejudice, The Seven Husbands of Evelyn Hugo |
| `dystopian future society` | 1984 |
| `fantasy magic adventure` | Circe, The Invisible Life of Addie LaRue |
| `science fiction space` | Project Hail Mary |
| `memoir personal growth` | Educated |
| `self improvement habits` | Atomic Habits |

### TV Shows

| Query | Expected Top Results |
|-------|---------------------|
| `crime drama drug dealer` | Breaking Bad |
| `supernatural kids 1980s` | Stranger Things |
| `historical royal family` | The Crown |
| `fantasy medieval dragons` | Game of Thrones |
| `time travel mystery` | Dark |
| `workplace comedy office` | The Office |
| `post apocalyptic survival` | The Last of Us |

### Mixed Queries

| Query | Expected Results |
|-------|------------------|
| `psychological thriller` | Books: The Silent Patient, 1984; TV: Breaking Bad |
| `comedy heartwarming` | TV: Ted Lasso, The Office, Fleabag |
| `epic fantasy adventure` | Books: Circe; TV: Game of Thrones, The Witcher |

## Acceptance Criteria Validation

This E2E test validates the following requirements:

- **Requirement 1.1**: User can submit queries via frontend ✓
- **Requirement 1.4**: Queries are forwarded to backend and ML Engine ✓
- **Requirement 4.1**: Metadata is retrieved from PostgreSQL ✓
- **Requirement 5.1**: JSON response contains results array ✓
- **Requirement 5.2**: Response includes query_time_ms ✓
- **Requirement 5.4**: Results sorted by similarity_score descending ✓
- **Requirement 6.1**: Frontend displays recommendations as cards ✓

## Next Steps

After completing E2E testing:

1. Document any issues found in GitHub Issues
2. Run automated test suite for regression testing
3. Perform load testing with multiple concurrent users
4. Test on different browsers (Chrome, Firefox, Safari)
5. Test on mobile devices (responsive design)
6. Prepare for production deployment

## Additional Resources

- API Documentation: http://localhost:8000/docs
- Backend Logs: Check terminal running `uvicorn`
- Frontend Logs: Browser DevTools Console
- Database Queries: Use `psql` or pgAdmin
- Vector DB UI: http://localhost:6333/dashboard (if enabled)
