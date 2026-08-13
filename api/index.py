import os
import sys
from pathlib import Path

# Fallback writable SQLite database path for Vercel Serverless environment
if "AGORA_SQLITE_PATH" not in os.environ:
    os.environ["AGORA_SQLITE_PATH"] = "/tmp/agora.db"

# Enable demo mode bypass by default on serverless showcase unless overridden
if "AGORA_DEMO_MODE" not in os.environ:
    os.environ["AGORA_DEMO_MODE"] = "1"

# Add server directory to Python path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "server"))

from app.main import app  # noqa: E402

# Export ASGI app for Vercel Python runtime
__all__ = ["app"]
