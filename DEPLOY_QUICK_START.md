# Quick Deployment Guide

## Fastest Way to Deploy

### Step 1: Deploy Backend to Railway (5 minutes)

1. Go to [railway.app](https://railway.app) and sign up
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Click "Add variables" and paste:
```
POSTGRES_HOST=your-db-host
POSTGRES_PORT=5432
POSTGRES_DB=semantic_media
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
USE_FILE_STORAGE=true
VECTOR_SIZE=768
VECTORIZER_TYPE=sbert
SBERT_MODEL_NAME=all-mpnet-base-v2
USE_HYBRID_SEARCH=true
VECTORIZER_PATH=./models
EMBEDDINGS_PATH=./embeddings
```
5. Add PostgreSQL database: Click "New" → "Database" → "PostgreSQL"
6. Railway will auto-detect Python and deploy
7. Copy your backend URL (e.g., `https://vibecheck-backend.up.railway.app`)

### Step 2: Deploy Frontend to Vercel (3 minutes)

1. Go to [vercel.com](https://vercel.com) and sign up
2. Click "Add New" → "Project"
3. Import your GitHub repository
4. Configure:
   - **Root Directory**: `frontend`
   - **Framework**: Next.js (auto-detected)
5. Add environment variable:
   - **Name**: `NEXT_PUBLIC_API_URL`
   - **Value**: Your Railway backend URL from Step 1
6. Click "Deploy"
7. Wait 2-3 minutes for build to complete

### Step 3: Upload Data to Railway

After backend deploys, you need to upload your data:

**Option A: Using Railway CLI**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Upload database dump
railway run psql < your_database_dump.sql
```

**Option B: Using pgAdmin or DBeaver**
1. Get database credentials from Railway dashboard
2. Connect using pgAdmin or DBeaver
3. Import your SQL dump or CSV files

### Step 4: Upload Embeddings

Your embeddings need to be uploaded to Railway:

```bash
# Connect to Railway
railway link

# Upload embeddings directory
railway run python -c "from database.file_vector_db import FileVectorDatabase; print('Upload embeddings manually')"
```

Or regenerate embeddings on Railway:
```bash
railway run python data_pipeline/migrate_to_sbert.py
```

## That's It!

Your app should now be live:
- **Frontend**: `https://your-app.vercel.app`
- **Backend**: `https://your-backend.up.railway.app`

## Troubleshooting

**Frontend can't connect to backend:**
- Check `NEXT_PUBLIC_API_URL` in Vercel environment variables
- Verify backend CORS settings allow your Vercel domain
- Test backend health: `https://your-backend.up.railway.app/health`

**Backend errors:**
- Check Railway logs for errors
- Verify all environment variables are set
- Ensure PostgreSQL database is connected
- Check if embeddings are uploaded

**Build failures:**
- Check build logs in Vercel/Railway dashboard
- Verify all dependencies are in package.json/requirements.txt
- Ensure Node.js/Python versions are compatible

## Alternative: Deploy Both to Railway

If you want everything in one place:

1. Create Railway project
2. Add two services:
   - Service 1: Backend (root: `backend`)
   - Service 2: Frontend (root: `frontend`)
3. Add PostgreSQL database
4. Set environment variables for both
5. Railway handles the rest

Cost: ~$10-15/month for both services + database
