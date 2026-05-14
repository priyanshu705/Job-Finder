"""
src/finder/scripts/migrate_resume_schema.py
-------------------------------------------
Idempotent migration script for the new resume_profile table.
Supports SQLite (local) and PostgreSQL (production).
"""

import sys
import os
import logging

# Ensure the parent directories are in the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from finder.shared.database import get_db, _USE_POSTGRES
from finder.shared.logging import get_logger

log = get_logger("migrate")

def migrate():
    """Run the schema migration for resume_profile."""
    log.info("Starting schema migration for resume_profile...", extra={"is_postgres": _USE_POSTGRES})

    # The new schema for the single-row profile table.
    schema_sql = """
        CREATE TABLE IF NOT EXISTS resume_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            filename TEXT,
            file_type TEXT,
            raw_text TEXT,
            skills TEXT,
            detected_roles TEXT,
            generated_queries TEXT,
            parsing_status TEXT,
            upload_size INTEGER,
            uploaded_at TIMESTAMP,
            updated_at TIMESTAMP
        );
    """

    try:
        with get_db() as conn:
            # 1. Create the table
            if _USE_POSTGRES:
                conn.execute(schema_sql)
            else:
                conn.executescript(schema_sql)
            
            log.info("Table resume_profile created or already exists.")

            # 2. Add safe indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_resume_uploaded_at ON resume_profile(uploaded_at);",
                "CREATE INDEX IF NOT EXISTS idx_resume_parsing_status ON resume_profile(parsing_status);"
            ]

            for idx_sql in indexes:
                try:
                    conn.execute(idx_sql)
                except Exception as e:
                    # Ignore errors if index already exists in older SQLite
                    log.warning("Index creation issue (likely exists): %s", e)
            
            log.info("Indexes verified.")
            
        log.info("Migration completed successfully.")
    except Exception as e:
        log.error("Migration failed: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    migrate()
