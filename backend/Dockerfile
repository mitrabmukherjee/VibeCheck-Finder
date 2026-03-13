# Keep image under Railway 4GB limit: slim base + CPU-only PyTorch
FROM python:3.12-slim

WORKDIR /app

# Install torch CPU-only first (much smaller than default PyTorch)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# App dependencies (sentence-transformers will use already-installed torch)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code (minimal; .dockerignore excludes tests, data_pipeline, embeddings, etc.)
COPY . .
# Ensure dirs exist so app startup doesn't fail (embeddings loaded from volume or Qdrant)
RUN mkdir -p models embeddings

EXPOSE 8000
ENV PORT=8000
# Railway injects PORT at runtime
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
