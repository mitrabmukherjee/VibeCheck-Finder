# Deploying VibeCheck Finder to Vercel

## Overview

Your app has two parts:
1. **Frontend** (Next.js) - Can be deployed to Vercel
2. **Backend** (Python FastAPI) - Needs to be deployed separately (Vercel doesn't support Python backends well)

## Option 1: Frontend Only on Vercel (Recommended for Testing)

### Step 1: Prepare Frontend

1. Make sure your frontend has a `.env.local` file:
```bash
cd frontend
cp .env.local.example .env.local
```

2. Update `frontend/.env.local` with your backend URL (you'll need to deploy backend first):
```
NEXT_PUBLIC_API_URL=https://your-backend-url.com
```

### Step 2: Deploy Frontend to Vercel

**Option A: Using Vercel CLI**

1. Install Vercel CLI:
```bash
npm install -g vercel
```

2. Login to Vercel:
```bash
vercel login
```

3. Deploy from the frontend directory:
```bash
cd frontend
vercel
```

4. Follow the prompts:
   - Set up and deploy? **Y**
   - Which scope? Select your account
   - Link to existing project? **N**
   - Project name? **vibecheck-finder** (or your choice)
   - In which directory is your code located? **.**
   - Want to override settings? **N**

5. For production deployment:
```bash
vercel --prod
```

**Option B: Using Vercel Dashboard**

1. Go to [vercel.com](https://vercel.com)
2. Click "Add New" → "Project"
3. Import your Git repository
4. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
5. Add environment variable:
   - Key: `NEXT_PUBLIC_API_URL`
   - Value: Your backend URL
6. Click "Deploy"

## Option 2: Full Stack Deployment

Since Vercel doesn't support Python backends well, you'll need to deploy the backend elsewhere.

### Backend Deployment Options

**Option A: Railway.app (Easiest)**

1. Go to [railway.app](https://railway.app)
2. Create new project from GitHub repo
3. Add PostgreSQL database from Railway
4. Set environment variables from `backend/.env.example`
5. Railway will auto-detect Python and deploy

**Option B: Render.com**

1. Go to [render.com](https://render.com)
2. Create new "Web Service"
3. Connect your GitHub repo
4. Configure:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add PostgreSQL database
6. Set environment variables

**Option C: Fly.io**

1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Create `backend/fly.toml`:
```toml
app = "vibecheck-backend"

[build]
  builder = "paketobuildpacks/builder:base"

[env]
  PORT = "8000"

[[services]]
  http_checks = []
  internal_port = 8000
  protocol = "tcp"

  [[services.ports]]
    force_https = true
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443
```

4. Deploy:
```bash
cd backend
fly launch
fly deploy
```

### After Backend Deployment

1. Get your backend URL (e.g., `https://vibecheck-backend.railway.app`)
2. Update frontend environment variable:
   - In Vercel dashboard → Settings → Environment Variables
   - Update `NEXT_PUBLIC_API_URL` to your backend URL
3. Redeploy frontend

## Option 3: Deploy Everything to Railway

Railway can host both frontend and backend:

1. Create new project on Railway
2. Add two services:
   - **Frontend**: Next.js app from `frontend` directory
   - **Backend**: Python app from `backend` directory
3. Add PostgreSQL database
4. Set environment variables for both services
5. Railway handles the rest

## Important Notes

### Backend Requirements

Your backend needs:
- PostgreSQL database (5,781 media items)
- Vector embeddings (768-dimensional, ~420MB)
- Python 3.9+ with dependencies
- At least 1GB RAM for the ML model

### Environment Variables

**Frontend** (`frontend/.env.local`):
```
NEXT_PUBLIC_API_URL=https://your-backend-url.com
```

**Backend** (set in hosting platform):
```
POSTGRES_HOST=your-db-host
POSTGRES_PORT=5432
POSTGRES_DB=semantic_media
POSTGRES_USER=your-user
POSTGRES_PASSWORD=your-password
USE_FILE_STORAGE=true
VECTOR_SIZE=768
VECTORIZER_TYPE=sbert
SBERT_MODEL_NAME=all-mpnet-base-v2
USE_HYBRID_SEARCH=true
VECTORIZER_PATH=./models
EMBEDDINGS_PATH=./embeddings
```

### Data Migration

After deploying the backend, you'll need to:

1. Upload your PostgreSQL data (5,781 items)
2. Upload vector embeddings or regenerate them
3. Run the migration script if needed

## Quick Start (Recommended)

1. **Deploy Backend First** to Railway:
   - Sign up at railway.app
   - Create new project from GitHub
   - Add PostgreSQL
   - Set environment variables
   - Get backend URL

2. **Deploy Frontend** to Vercel:
   - Sign up at vercel.com
   - Import GitHub repo
   - Set root directory to `frontend`
   - Add `NEXT_PUBLIC_API_URL` environment variable
   - Deploy

3. **Migrate Data**:
   - Connect to Railway PostgreSQL
   - Import your data
   - Upload embeddings or regenerate

## Cost Estimates

- **Vercel**: Free tier (hobby projects)
- **Railway**: ~$5-10/month (includes PostgreSQL)
- **Render**: Free tier available (limited resources)

## Need Help?

If you run into issues:
1. Check build logs in your hosting platform
2. Verify environment variables are set correctly
3. Test backend health endpoint: `https://your-backend-url.com/health`
4. Check CORS settings in backend allow your frontend domain
