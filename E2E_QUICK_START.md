# E2E Testing Quick Start Guide
## Semantic Media Engine

Get started with end-to-end testing in 5 minutes.

## Prerequisites

Ensure these services are running:

```bash
# 1. PostgreSQL
pg_isready -h localhost -p 5432

# 2. Qdrant
curl http://localhost:6333/health

# 3. Sample data loaded
psql -d semantic_media -c "SELECT COUNT(*) FROM media_items;"
```

If any service is not ready, see [E2E_TROUBLESHOOTING.md](E2E_TROUBLESHOOTING.md).

## Step 1: Start Backend

```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verify: http://localhost:8000/health should return `{"status": "healthy"}`

## Step 2: Start Frontend (Optional for Manual Testing)

In a new terminal:

```bash
cd frontend
npm run dev
```

Verify: http://localhost:3000 should show the search interface

## Step 3: Run Automated Tests

In a new terminal:

```bash
# Simple run
python test_e2e.py

# Verbose output
python test_e2e.py --verbose

# Custom backend URL
python test_e2e.py --backend-url http://127.0.0.1:8000
```

## Step 4: Manual Testing (Optional)

1. Open http://localhost:3000
2. Try these queries:
   - `mystery book with detective`
   - `science fiction show about time travel`
   - `romantic period drama`

Expected: Results appear within 1-2 seconds with similarity scores.

## Quick Test Commands

```bash
# Test backend directly with curl
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "mystery thriller", "top_k": 5}'

# Run automated test suite
python test_e2e.py

# Run with test runner script
./run_e2e_tests.sh  # Linux/Mac
run_e2e_tests.bat   # Windows
```

## Expected Results

### Automated Tests
- 8 tests should pass
- Total duration: < 10 seconds
- All query times: < 1 second

### Manual Tests
- Loading indicator appears immediately
- Results load within 1-2 seconds
- 3-5 recommendations displayed
- Similarity scores between 50-95%

## Troubleshooting

**Backend won't start?**
- Check `.env` file exists and is configured
- Verify PostgreSQL and Qdrant are running
- Check logs for specific errors

**No results returned?**
- Verify sample data: `psql -d semantic_media -c "SELECT COUNT(*) FROM media_items;"`
- Check vectorizer exists: `ls backend/models/vectorizer.pkl`
- Re-run data pipeline if needed

**CORS errors?**
- Check `CORS_ORIGINS` in `backend/.env` includes `http://localhost:3000`
- Restart backend after changing `.env`

See [E2E_TROUBLESHOOTING.md](E2E_TROUBLESHOOTING.md) for detailed solutions.

## Next Steps

- Review [E2E_TESTING_GUIDE.md](E2E_TESTING_GUIDE.md) for comprehensive testing instructions
- Check [TEST_QUERIES.md](TEST_QUERIES.md) for more query examples
- Run tests on different browsers and devices
- Perform load testing with multiple concurrent users
