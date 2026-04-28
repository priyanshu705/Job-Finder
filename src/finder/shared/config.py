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

# Resume
RESUME_PATH = os.getenv("RESUME_PATH", os.path.join(RESUME_DIR, "resume.pdf"))

# Ensure directories exist (file-system directories only — skip in PG-only mode)
os.makedirs(DATA_DIR,       exist_ok=True)
os.makedirs(LOGS_DIR,       exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(RESUME_DIR,     exist_ok=True)

