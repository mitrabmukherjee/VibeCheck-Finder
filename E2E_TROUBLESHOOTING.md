# E2E Testing Troubleshooting Guide
## Semantic Media Engine

Quick reference for resolving common E2E testing issues.

## Pre-Test Checklist

Before running E2E tests, verify:

- [ ] PostgreSQL is running (`pg_isready`)
- [ ] Qdrant is running (`curl http://localhost:6333/health`)
- [ ] Database `semantic_media` exists
- [ ] Sample data is loaded (check with `psql -d semantic_media -c "SELECT COUNT(*) FROM media_items;"`)
- [ ] Backend `.env` file is configured
- [ ] Frontend `.env.local` file is configured
- [ ] Vectorizer model exists (`backend/models/vectorizer.pkl`)
- [ ] Backend virtual environment is activated

## Common Issues

### Issue 1: Backend Won't Start

**Symptoms:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

**Symptoms:**
```
ERROR: ML Engine not initialized
```

**Solution:**
1. Check vectorizer model exists: `ls backend/models/vectorizer.pkl`
2. If missing, run data pipeline: `python backend/data_pipeline/run_sample_pipeline.py`
3. Verify `VECTORIZER_PATH` in `.env` is correct

---

**Symptoms:**
```
ERROR: Database service unavailable
```

**Solution:**
1. Check PostgreSQL: `pg_isready -h localhost -p 5432`
2. Verify database exists: `psql -l | grep semantic_media`
3. Check credentials in `backend/.env`
4. Test connection: `psql -d semantic_media -c "SELECT 1;"`


### Issue 2: Frontend Won't Start

**Symptoms:**
```
Error: Cannot find module 'next'
```

**Solution:**
```bash
cd frontend
npm install
```

---

**Symptoms:**
```
Error: NEXT_PUBLIC_API_URL is not defined
```

**Solution:**
```bash
cd frontend
cp .env.local.example .env.local
# Edit .env.local and set NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Issue 3: CORS Errors

**Symptoms:**
```
Access to fetch at 'http://localhost:8000/recommend' from origin 
'http://localhost:3000' has been blocked by CORS policy
```

**Solution:**
1. Check `CORS_ORIGINS` in `backend/.env`:
   ```
   CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
   ```
2. Restart backend server after changing `.env`
3. Clear browser cache (Ctrl+Shift+Delete)
4. Try hard refresh (Ctrl+F5)

### Issue 4: No Results Returned

**Symptoms:**
- All queries return empty results
- "No recommendations found" for every query

**Solution:**
1. Verify sample data is loaded:
   ```bash
   psql -d semantic_media -c "SELECT COUNT(*) FROM media_items;"
   ```
2. Check Qdrant has embeddings:
   ```bash
   curl http://localhost:6333/collections/media_embeddings
   ```
3. If no data, run data pipeline:
   ```bash
   cd backend
   python data_pipeline/run_sample_pipeline.py
   ```

### Issue 5: Slow Performance

**Symptoms:**
- Queries take > 2 seconds
- Loading spinner visible for long time

**Solution:**
1. Check if Qdrant is running locally (not remote)
2. Verify vectorizer is loaded (not re-training):
   ```bash
   ls -lh backend/models/vectorizer.pkl
   ```
3. Check system resources (CPU, memory)
4. Reduce `top_k` parameter if requesting many results
5. Check database connection latency


### Issue 6: Test Script Fails

**Symptoms:**
```
ModuleNotFoundError: No module named 'requests'
```

**Solution:**
```bash
pip install requests
```

---

**Symptoms:**
```
Connection refused to http://localhost:8000
```

**Solution:**
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check backend logs for errors
3. Ensure port 8000 is not blocked by firewall
4. Try `http://127.0.0.1:8000` instead

### Issue 7: Database Connection Errors

**Symptoms:**
```
psycopg2.OperationalError: could not connect to server
```

**Solution:**
1. Check PostgreSQL is running: `pg_isready`
2. Verify connection parameters in `.env`:
   ```
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_password
   ```
3. Test connection manually:
   ```bash
   psql -h localhost -p 5432 -U postgres -d semantic_media
   ```

### Issue 8: Qdrant Connection Errors

**Symptoms:**
```
ConnectionError: Failed to connect to Qdrant
```

**Solution:**
1. Check Qdrant is running:
   ```bash
   curl http://localhost:6333/health
   ```
2. If not running, start with Docker:
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   ```
3. Verify `QDRANT_HOST` and `QDRANT_PORT` in `.env`

## Diagnostic Commands

### Check All Services
```bash
# PostgreSQL
pg_isready -h localhost -p 5432

# Qdrant
curl http://localhost:6333/health

# Backend
curl http://localhost:8000/health

# Frontend (if running)
curl http://localhost:3000
```

### Check Data
```bash
# Media items count
psql -d semantic_media -c "SELECT COUNT(*) FROM media_items;"

# Media type distribution
psql -d semantic_media -c "SELECT media_type, COUNT(*) FROM media_items GROUP BY media_type;"

# Qdrant collection info
curl http://localhost:6333/collections/media_embeddings
```

### Check Logs
```bash
# Backend logs (in terminal running uvicorn)
# Look for errors during startup or request processing

# PostgreSQL logs
tail -f /var/log/postgresql/postgresql-*.log

# Qdrant logs (if using Docker)
docker logs <qdrant-container-id>
```

## Quick Reset

If all else fails, reset the environment:

```bash
# 1. Stop all services
# Ctrl+C in backend terminal
# Ctrl+C in frontend terminal
docker stop <qdrant-container-id>

# 2. Clear data
psql -d semantic_media -c "DROP TABLE IF EXISTS media_items CASCADE;"
curl -X DELETE http://localhost:6333/collections/media_embeddings

# 3. Restart services
docker run -p 6333:6333 qdrant/qdrant

# 4. Recreate database schema
cd backend
python database/migrate.py

# 5. Load sample data
python data_pipeline/run_sample_pipeline.py

# 6. Start backend
uvicorn main:app --reload

# 7. Start frontend (in new terminal)
cd frontend
npm run dev

# 8. Run tests
python test_e2e.py
```

## Getting Help

If issues persist:

1. Check backend logs for detailed error messages
2. Check browser console (F12) for frontend errors
3. Review the E2E_TESTING_GUIDE.md for detailed instructions
4. Verify all prerequisites are met
5. Try the Quick Reset procedure above
