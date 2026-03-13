# Deploy Backend on Render (easier)

[Render](https://render.com) is often simpler than Railway: connect GitHub, add Postgres with one click, and deploy. No Docker or image size limits to worry about.

---

## Option A: One-click from Blueprint (easiest)

1. Go to [render.com](https://render.com) and sign in with GitHub.
2. Click **New** → **Blueprint**.
3. Connect your **VibeCheck-finder** repository.
4. Render will read **`render.yaml`** and create:
   - A **PostgreSQL** database
   - A **Web Service** (your FastAPI backend) with the database URL set automatically.
5. When prompted for **CORS_ORIGINS**, enter your frontend URL (e.g. `https://your-app.vercel.app`).
6. Click **Apply**. Render will build and deploy.
7. Copy your backend URL (e.g. `https://vibecheck-backend.onrender.com`) and set **NEXT_PUBLIC_API_URL** in your Vercel frontend to that URL.

**Note:** On the free plan the backend may spin down after 15 minutes of no traffic; the first request after that can be slow.

---

## Option B: Manual setup (same result, step by step)

1. **New** → **PostgreSQL** → create a database (free tier is fine). Copy the **Internal Database URL**.
2. **New** → **Web Service** → connect your repo.
3. Settings:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Environment:**
   - Add **DATABASE_URL** = the Internal Database URL from step 1.
   - Add **CORS_ORIGINS** = your Vercel frontend URL.
   - Add the rest from the table in **DEPLOY_RAILWAY_BACKEND.md** (USE_FILE_STORAGE, VECTOR_*, etc.) or leave defaults if the blueprint already set them.
5. Deploy. Use the service URL as **NEXT_PUBLIC_API_URL** in Vercel.

---

## Summary

| Step | Action |
|------|--------|
| 1 | Render → New → Blueprint → connect repo |
| 2 | Enter CORS_ORIGINS when prompted (your frontend URL) |
| 3 | Apply → copy backend URL → set NEXT_PUBLIC_API_URL in Vercel |

The backend now supports **DATABASE_URL** (one connection string from Render), so you don’t need to set POSTGRES_HOST, POSTGRES_PORT, etc. manually.
