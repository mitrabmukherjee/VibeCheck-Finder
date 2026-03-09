# Qdrant Vector Database Setup Guide

This guide provides multiple options for setting up Qdrant Vector Database for the Semantic Media Engine.

## Option 1: Install Docker Desktop (Recommended)

Docker is the easiest way to run Qdrant. Here's how to install it on Windows:

### Step 1: Download Docker Desktop

1. Visit: https://www.docker.com/products/docker-desktop/
2. Click "Download for Windows"
3. Run the installer (Docker Desktop Installer.exe)

### Step 2: Install Docker Desktop

1. Follow the installation wizard
2. When prompted, ensure "Use WSL 2 instead of Hyper-V" is checked (recommended)
3. Complete the installation and restart your computer if prompted

### Step 3: Start Docker Desktop

1. Launch Docker Desktop from the Start menu
2. Wait for Docker to start (you'll see "Docker Desktop is running" in the system tray)
3. You may need to accept the Docker Subscription Service Agreement

### Step 4: Verify Docker Installation

Open PowerShell or Command Prompt and run:

```bash
docker --version
```

You should see output like: `Docker version 24.0.x, build xxxxx`

### Step 5: Start Qdrant with Docker

Once Docker is running, start Qdrant:

```bash
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
```

This will:
- Download the Qdrant image (first time only)
- Start Qdrant in the background
- Expose it on port 6333

### Step 6: Verify Qdrant is Running

```bash
curl http://localhost:6333/health
```

Or visit in your browser: http://localhost:6333/dashboard

### Managing Qdrant Container

**Stop Qdrant:**
```bash
docker stop qdrant
```

**Start Qdrant (after stopping):**
```bash
docker start qdrant
```

**Remove Qdrant container:**
```bash
docker rm -f qdrant
```

**View Qdrant logs:**
```bash
docker logs qdrant
```

---

## Option 2: Install Qdrant Locally (Without Docker)

If you prefer not to use Docker, you can install Qdrant directly on Windows.

### Step 1: Download Qdrant Binary

1. Visit: https://github.com/qdrant/qdrant/releases
2. Download the latest Windows binary (e.g., `qdrant-x86_64-pc-windows-msvc.zip`)
3. Extract the ZIP file to a folder (e.g., `C:\qdrant`)

### Step 2: Run Qdrant

Open PowerShell or Command Prompt and navigate to the Qdrant folder:

```bash
cd C:\qdrant
.\qdrant.exe
```

Qdrant will start and listen on port 6333 by default.

### Step 3: Verify Qdrant is Running

```bash
curl http://localhost:6333/health
```

Or visit: http://localhost:6333/dashboard

---

## Option 3: Use Qdrant Cloud (Free Tier)

Qdrant offers a free cloud tier that doesn't require local installation.

### Step 1: Sign Up for Qdrant Cloud

1. Visit: https://cloud.qdrant.io/
2. Sign up for a free account
3. Create a new cluster (free tier: 1GB storage)

### Step 2: Get Your Cluster URL and API Key

1. After creating the cluster, note the cluster URL (e.g., `https://xxx-xxx.aws.cloud.qdrant.io`)
2. Generate an API key from the dashboard

### Step 3: Update Your Backend Configuration

Edit `backend/.env`:

```bash
# Qdrant Cloud Configuration
QDRANT_HOST=https://xxx-xxx.aws.cloud.qdrant.io
QDRANT_PORT=443
QDRANT_API_KEY=your_api_key_here
```

Update `backend/database/vector_db.py` to use the API key:

```python
# In VectorDatabase.__init__
if api_key:
    self.client = QdrantClient(
        url=f"{host}:{port}",
        api_key=api_key,
        https=True
    )
```

---

## Troubleshooting

### Issue: "Docker Desktop requires Windows 10/11"

**Solution:** Use Option 2 (local binary) or Option 3 (cloud)

### Issue: "WSL 2 installation is incomplete"

**Solution:** 
1. Open PowerShell as Administrator
2. Run: `wsl --install`
3. Restart your computer
4. Try Docker Desktop installation again

### Issue: "Port 6333 is already in use"

**Solution:**
1. Check if Qdrant is already running: `docker ps`
2. Stop the existing container: `docker stop qdrant`
3. Or use a different port: `docker run -d -p 6334:6333 qdrant/qdrant`
   (Update `QDRANT_PORT=6334` in `.env`)

### Issue: "Cannot connect to Docker daemon"

**Solution:**
1. Ensure Docker Desktop is running (check system tray)
2. Restart Docker Desktop
3. If still failing, restart your computer

### Issue: Qdrant connection refused

**Solution:**
1. Verify Qdrant is running: `docker ps` or check process manager
2. Check firewall settings (allow port 6333)
3. Try accessing: http://localhost:6333/dashboard

---

## Next Steps After Qdrant is Running

Once Qdrant is running, you can proceed with the Netflix data pipeline:

```bash
cd backend
python data_pipeline/run_netflix_pipeline.py
```

This will:
1. Load the converted Netflix dataset (500 items)
2. Train the TF-IDF vectorizer
3. Generate embeddings for all descriptions
4. Store embeddings in Qdrant
5. Store metadata in PostgreSQL

---

## Quick Start Commands

**With Docker (Recommended):**
```bash
# Start Qdrant
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant

# Verify it's running
curl http://localhost:6333/health

# Run the Netflix pipeline
cd backend
python data_pipeline/run_netflix_pipeline.py
```

**Without Docker:**
```bash
# Start Qdrant (in one terminal)
cd C:\qdrant
.\qdrant.exe

# Run the Netflix pipeline (in another terminal)
cd backend
python data_pipeline/run_netflix_pipeline.py
```

---

## Resources

- Docker Desktop: https://www.docker.com/products/docker-desktop/
- Qdrant Documentation: https://qdrant.tech/documentation/
- Qdrant GitHub: https://github.com/qdrant/qdrant
- Qdrant Cloud: https://cloud.qdrant.io/

---

## Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Review Qdrant logs: `docker logs qdrant`
3. Visit Qdrant documentation: https://qdrant.tech/documentation/quick-start/
