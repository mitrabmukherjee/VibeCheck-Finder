"""
Vercel entrypoint: expose the FastAPI app so Vercel can discover it at app.py.
"""
from main import app
