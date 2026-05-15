"""
Celery worker entrypoint.
Usage: celery -A celery_worker.celery worker --loglevel=info --pool=solo
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv

load_dotenv()

from finder.shared.celery_app import celery_app as celery  # noqa: E402,F401
