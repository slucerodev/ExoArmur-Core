"""
Production entry point for the ExoArmur HTTP API.

Usage:
    uvicorn scripts.run_api:app --host 0.0.0.0 --port 8000

This script replaces the broken `exoarmur.main:app` reference in the
Dockerfile and provides the actual runnable FastAPI application.
"""

import os

# Ensure deterministic environment before any other imports
os.environ.setdefault("PYTHONHASHSEED", "0")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

from exoarmur.api.server import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "scripts.run_api:app",
        host=os.getenv("EXOARMUR_API_HOST", "0.0.0.0"),
        port=int(os.getenv("EXOARMUR_API_PORT", "8000")),
        reload=os.getenv("EXOARMUR_API_RELOAD", "false").lower() == "true",
    )
