"""
Production app entrypoint for Gunicorn.
Usage: gunicorn app:app
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv

load_dotenv()

from finder.api.main import app as app  # noqa: E402,F401
