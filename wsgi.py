"""
wsgi.py
-------
WSGI entry point for Gunicorn (production).
"""
import os
import sys

# Ensure src/ is on the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv
load_dotenv()

# Initialize the database schema on first boot
from finder.shared.database import init_db
try:
    init_db()
except Exception as e:
    print(f"[wsgi] DB init warning: {e}")

from finder.api.main import app  # noqa: E402

if __name__ == "__main__":
    app.run()
