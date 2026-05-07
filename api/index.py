"""
Vercel serverless entry point.
Vercel's Python builder looks for `app` in api/index.py (among other paths).
We simply add the project root to sys.path and re-export the FastAPI app.
"""
import sys
import os

# Make the project root importable so `from backend.main import app` works.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app  # noqa: F401  – Vercel uses this `app` variable
