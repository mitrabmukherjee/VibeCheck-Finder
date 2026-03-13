# Deploy to Vercel

**Recommended:** Deploy the **frontend** (Next.js) on Vercel and the **backend** (FastAPI) on **Render** or **Railway**.

- **Easier:** **[DEPLOY_RENDER_BACKEND.md](DEPLOY_RENDER_BACKEND.md)** — Connect repo → Blueprint → one-click Postgres + backend. No Docker or image limits.
- **Alternative:** [DEPLOY_RAILWAY_BACKEND.md](DEPLOY_RAILWAY_BACKEND.md) (Railway; more config, 4 GB image limit).

You can also run the backend on Vercel as a serverless function (see [§2b](#2b-deploy-backend-on-vercel-optional)).

---

## 1. Deploy frontend to Vercel

### Option A: Vercel Dashboard (recommended)

1. Go to [vercel.com](https://vercel.com) and sign in (GitHub is easiest).
2. **Add New** → **Project**.
3. Import your Git repository (`VibeCheck-finder`).
4. **Configure:**
   - **Root Directory:** Click **Edit**, choose `frontend`, then **Save**.
   - **Framework Preset:** Next.js (auto-detected).
   - **Build Command:** `npm run build` (default).
   - **Output Directory:** `.next` (default).
5. **Environment variables:** Add:
   - **Name:** `NEXT_PUBLIC_API_URL`
   - **Value:** Your backend URL (e.g. `https://your-backend.up.railway.app` from Railway—see [DEPLOY_RAILWAY_BACKEND.md](DEPLOY_RAILWAY_BACKEND.md); or leave as `http://localhost:8000` for dev and change later).
6. Click **Deploy**. Vercel will build and deploy the frontend.

After deploy, you’ll get a URL like `https://vibecheck-finder-xxx.vercel.app`.

### Option B: Vercel CLI

```bash
# Install and log in (one-time)
npm i -g vercel
vercel login

# Deploy from repo root (Vercel will use frontend if you set Root Directory in the linked project)
cd frontend
vercel

# Link to existing project or create new; when asked for root, use . (current dir = frontend)
# Add env in dashboard: Project → Settings → Environment Variables → NEXT_PUBLIC_API_URL

# Production
vercel --prod
```

---

## 2a. Deploy backend (recommended: Render)

**Easiest:** **→ [DEPLOY_RENDER_BACKEND.md](DEPLOY_RENDER_BACKEND.md)** — Use Render’s Blueprint: connect repo, get Postgres + backend in one go. Then set `NEXT_PUBLIC_API_URL` in Vercel to your Render backend URL.

**Alternative (Railway):** [DEPLOY_RAILWAY_BACKEND.md](DEPLOY_RAILWAY_BACKEND.md) — More setup (Root Directory, env vars, Docker/image size). Then set `NEXT_PUBLIC_API_URL` to your Railway backend URL.

---

## 2b. Deploy backend on Vercel (optional)

The FastAPI backend can also run on Vercel as a **serverless function**. You need a **second Vercel project** (backend only).

### Backend project setup

1. In Vercel: **Add New** → **Project**.
2. Import the **same** Git repository (`VibeCheck-finder`).
3. **Configure:**
   - **Root Directory:** Click **Edit**, choose `backend`, then **Save**.
   - **Framework Preset:** Other (or leave as detected).
   - Do **not** set a Build Command unless you need one; Vercel will use `requirements.txt` and detect the FastAPI app.
4. **Environment variables** (required): Add all of these (values from your hosted services):

   | Name | Example / notes |
   |------|------------------|
   | `POSTGRES_HOST` | Your Postgres host (e.g. from Neon, Supabase, Railway) |
   | `POSTGRES_PORT` | `5432` |
   | `POSTGRES_DB` | Your DB name |
   | `POSTGRES_USER` | DB user |
   | `POSTGRES_PASSWORD` | DB password |
   | `CORS_ORIGINS` | Your frontend URL, e.g. `https://your-frontend.vercel.app` |
   | `USE_FILE_STORAGE` | `true` or `false` (see below) |
   | `VECTOR_SIZE` | `768` (for SBERT) |
   | `VECTORIZER_TYPE` | `sbert` |
   | `SBERT_MODEL_NAME` | `all-MiniLM-L6-v2` (smaller model recommended for Vercel; `all-mpnet-base-v2` is larger) |
   | `VECTORIZER_PATH` | `models` |
   | `EMBEDDINGS_PATH` | `embeddings` (or use Qdrant; see below) |
   | `USE_HYBRID_SEARCH` | `true` or `false` |

5. Click **Deploy**. Your backend URL will be like `https://your-backend-project.vercel.app`.

### Backend on Vercel: important constraints

- **PostgreSQL:** Use a **hosted** Postgres (e.g. [Neon](https://neon.tech), [Supabase](https://supabase.com), Railway). Set the env vars above. Serverless does not run a local DB.
- **Vector DB:**
  - **Option A:** `USE_FILE_STORAGE=true` and ship embeddings in the repo under `backend/embeddings`. The serverless bundle must stay under **500 MB** (uncompressed). If your embeddings are large, use Option B.
  - **Option B:** `USE_FILE_STORAGE=false` and use **hosted Qdrant** (e.g. [Qdrant Cloud](https://cloud.qdrant.io)). Set `QDRANT_HOST` and `QDRANT_PORT` (and auth if required).
- **SBERT model:** The first request (cold start) can be slow while the model loads. Using `SBERT_MODEL_NAME=all-MiniLM-L6-v2` keeps the bundle smaller; `all-mpnet-base-v2` is larger and may push you toward the 500 MB limit.
- **Timeouts:** Backend is configured for 60 s and 3 GB memory in `backend/vercel.json`. You can change `maxDuration` / `memory` there or in Project Settings.

### Backend deploy via CLI

```bash
cd backend
vercel
# Set Root Directory to . when linking; add env vars in dashboard
vercel --prod
```

---

## 3. Connect frontend to backend

1. In Vercel: **Project** → **Settings** → **Environment Variables**.
2. Set or update:
   - **Name:** `NEXT_PUBLIC_API_URL`
   - **Value:** `https://your-backend-url.com` (no trailing slash).
3. **Redeploy** the frontend (Deployments → ⋮ → Redeploy) so the new value is applied.

---

## 4. CORS

In your backend env, set `CORS_ORIGINS` (or equivalent) to include your Vercel URL, e.g.:

- `https://your-project.vercel.app`
- `https://*.vercel.app` (if your platform supports it)

Otherwise the browser will block API requests.

---

## Summary

| Part     | Where to deploy | Notes                                                                 |
|----------|------------------|-----------------------------------------------------------------------|
| Frontend | **Vercel**       | Root Directory = `frontend`; set `NEXT_PUBLIC_API_URL` to backend URL |
| Backend  | **Render**       | Easiest: **DEPLOY_RENDER_BACKEND.md** (Blueprint one-click)            |
| Backend  | Railway          | **DEPLOY_RAILWAY_BACKEND.md** (Docker, 4 GB limit)                   |
| Backend  | Vercel (optional) | Section 2b; serverless, 500 MB limit                               |

More options (Render, Fly.io): **VERCEL_DEPLOYMENT_GUIDE.md**.
