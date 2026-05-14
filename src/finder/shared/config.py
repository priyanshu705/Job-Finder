"""
src/finder/shared/config.py
---------------------------
Centralized configuration and path management.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Resolve project root (4 levels up from this file)
# src/finder/shared/config.py -> shared -> finder -> src -> root
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Paths
DATA_DIR       = os.path.join(PROJECT_ROOT, "data")
LOGS_DIR       = os.path.join(PROJECT_ROOT, "logs")
SCREENSHOT_DIR = os.path.join(LOGS_DIR, "screenshots")
RESUME_DIR     = os.path.join(PROJECT_ROOT, "resumes")

# Database — only compute a filesystem path when we're actually using SQLite.
_raw_db_url = os.getenv("DATABASE_URL", "")
_is_postgres = _raw_db_url.startswith("postgresql://") or _raw_db_url.startswith("postgres://")

if _is_postgres:
    # PostgreSQL mode: DB_PATH is irrelevant; set to None so importers don't
    # accidentally use it as a real path.
    DB_PATH = None
else:
    _db_ref = _raw_db_url.replace("sqlite:///", "") if _raw_db_url else ""
    if _db_ref and os.path.isabs(_db_ref):
        DB_PATH = _db_ref
    elif _db_ref:
        DB_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, _db_ref))
    else:
        DB_PATH = os.path.join(DATA_DIR, "finder.db")

# ── Phase 1B: Resume API Configuration ───────────────────────────────────────

# File limits and types
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 5 * 1024 * 1024)) # 5MB limit
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
ALLOWED_RESUME_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
}

# Parsing limits
PARSER_TIMEOUT_SECONDS = int(os.getenv("PARSER_TIMEOUT_SECONDS", 10))
ENABLE_RESUME_UPLOADS = os.getenv("ENABLE_RESUME_UPLOADS", "true").lower() == "true"

# Fallback basic resume path
RESUME_PATH = os.getenv("RESUME_PATH", os.path.join(RESUME_DIR, "resume.pdf"))

# Future-proofing placeholders
FUTURE_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
FUTURE_JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-change-in-prod")

def get_resume_upload_dir() -> str:
    """
    Returns the configured resume upload directory, ensuring it exists.
    Safe for runtime usage without import-side-effects.
    """
    directory = os.getenv("RESUME_DIR", RESUME_DIR)
    os.makedirs(directory, exist_ok=True)
    return directory

# Ensure base directories exist (file-system directories only — skip in PG-only mode)
os.makedirs(DATA_DIR,       exist_ok=True)
os.makedirs(LOGS_DIR,       exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
# Avoid creating RESUME_DIR here at import time if we want to defer it.
# We keep it for backwards compatibility with the rest of the app for now.
os.makedirs(RESUME_DIR,     exist_ok=True)
