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
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Paths
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
SCREENSHOT_DIR = os.path.join(LOGS_DIR, "screenshots")
RESUME_DIR = os.path.join(PROJECT_ROOT, "resumes")

# Database
DEFAULT_DB_PATH = os.path.join(DATA_DIR, "finder.db")
db_url = os.getenv("DATABASE_URL", DEFAULT_DB_PATH).replace("sqlite:///", "")
# Ensure DB_PATH is absolute if it's just a filename
if not os.path.isabs(db_url) and not db_url.startswith("http"):
    DB_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, db_url))
else:
    DB_PATH = db_url

# Resume
RESUME_PATH = os.getenv("RESUME_PATH", os.path.join(RESUME_DIR, "resume.pdf"))

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(RESUME_DIR, exist_ok=True)
