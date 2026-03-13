# Deploy Backend on Railway

Use this guide to run the FastAPI backend on [Railway](https://railway.app). Pair it with the frontend on Vercel (see **DEPLOY_VERCEL.md**).

---

## 1. Create project and add PostgreSQL

1. Go to [railway.app](https://railway.app) and sign in (e.g. with GitHub).
2. **New Project** → **Deploy from GitHub repo**.
3. Select your **VibeCheck-finder** repository.
4. In the new service, open **Settings**:
   - Set **Root Directory** to **`backend`** (required—building from repo root would include the frontend and exceed the 4 GB image limit).
   - Railway will detect the **Dockerfile** in `backend/` and use it (slim image + CPU-only PyTorch to stay under 4 GB). If no Dockerfile were present, it would use `railway.json` for the start command.
5. In the same project, add a database: **New** → **Database** → **PostgreSQL**.
6. In the **PostgreSQL** service, open **Variables** or **Connect** and note the credentials (host, port, database, user, password).

---

## 2. Configure backend environment variables

In your **backend service** (the one from the repo), go to **Variables** and add:

| Variable | Value |
|----------|--------|
| `POSTGRES_HOST` | From PostgreSQL service (e.g. `monorail.proxy.rlwy.net`) |
| `POSTGRES_PORT` | `5432` (or value from PostgreSQL) |
| `POSTGRES_DB` | Database name from PostgreSQL |
| `POSTGRES_USER` | User from PostgreSQL |
| `POSTGRES_PASSWORD` | Password from PostgreSQL |
| `CORS_ORIGINS` | Your frontend URL, e.g. `https://your-app.vercel.app` |
| `USE_FILE_STORAGE` | `true` (or `false` if you use Qdrant) |
| `VECTOR_SIZE` | `384` for all-MiniLM-L6-v2, or `768` for all-mpnet-base-v2 |
| `VECTORIZER_TYPE` | `sbert` |
| `SBERT_MODEL_NAME` | `all-MiniLM-L6-v2` or `all-mpnet-base-v2` |
| `VECTORIZER_PATH` | `models` |
| `EMBEDDINGS_PATH` | `embeddings` |
| `USE_HYBRID_SEARCH` | `true` |

**Optional:** `TMDB_API_KEY` if you use TMDB posters.

If you use **Qdrant** instead of file-based vectors, set `USE_FILE_STORAGE=false` and add `QDRANT_HOST`, `QDRANT_PORT` (and auth if needed).

---

## 3. Connect PostgreSQL to the backend service

- In the **backend** service, open **Variables** (or **Settings** → **Variables**).
- Either use **Add variable** → **Add reference** and pick the PostgreSQL service variables, or copy the values from the PostgreSQL service and paste them as plain variables (as in the table above).

Railway can also inject `DATABASE_URL`; if you use that, your app would need to parse it into `POSTGRES_*`. Using the separate `POSTGRES_*` vars matches the current backend.

---

## 4. Generate a public URL

1. In the **backend** service, open **Settings** → **Networking** (or **Variables** → **Networking**).
2. Click **Generate Domain**.
3. Copy the URL (e.g. `https://vibecheck-backend.up.railway.app`).

---

## 5. Point the frontend at the backend

In your **Vercel** project (frontend):

1. **Settings** → **Environment Variables**.
2. Set **`NEXT_PUBLIC_API_URL`** to your Railway backend URL (e.g. `https://vibecheck-backend.up.railway.app`), no trailing slash.
3. **Redeploy** the frontend so the new value is used.

---

## 6. Data and embeddings

- **PostgreSQL:** Create tables and load data (e.g. run migrations, then import your dump or CSV). You can use **Railway CLI** and `railway run` to run commands in the backend environment, or connect with a DB client using the PostgreSQL credentials.
- **Embeddings:** With `USE_FILE_STORAGE=true`, embeddings must be under `backend/embeddings` (or the path you set in `EMBEDDINGS_PATH`). Either commit them in the repo (if small enough) or upload them after deploy (e.g. via CLI or a one-off script). Alternatively use **Qdrant** and set `USE_FILE_STORAGE=false` with the right `QDRANT_*` vars.

---

## Image size (4 GB limit)

Railway limits images to **4 GB**. This repo is set up to stay under that:

- **Root Directory** must be **`backend`**. If you use the repo root, the build includes the frontend and can reach ~9 GB and fail.
- **`backend/Dockerfile`** uses `python:3.12-slim` and installs **CPU-only PyTorch** first, then the rest of the dependencies, which keeps the image smaller.
- **`backend/.dockerignore`** excludes tests, `data_pipeline/`, `data/`, and `embeddings/` so they are not sent in the build context.

If your image still exceeds 4 GB (e.g. large files in `models/`), add `models/` to `backend/.dockerignore`, or consider upgrading your Railway plan for a higher limit.

---

## Summary

| Step | Action |
|------|--------|
| 1 | New project → Deploy from GitHub → set **Root Directory** = `backend` |
| 2 | Add **PostgreSQL** in the same project |
| 3 | Set **Variables** on the backend service (Postgres, CORS, vectorizer, paths) |
| 4 | **Generate Domain** for the backend service |
| 5 | Set **NEXT_PUBLIC_API_URL** in Vercel to the Railway backend URL and redeploy |

When using the **Dockerfile**, the start command is inside the image. Otherwise **`backend/railway.json`** defines: `uvicorn main:app --host 0.0.0.0 --port $PORT`.
