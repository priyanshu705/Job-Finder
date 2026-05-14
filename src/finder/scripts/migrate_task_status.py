"""
src/finder/scripts/migrate_task_status.py
-----------------------------------------
Migration script for the task_status table to track Celery tasks.
Safe to run on both SQLite and PostgreSQL.
"""
import sys
import os

# Ensure finder module is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from finder.shared.database import get_db
from finder.shared.logging import get_logger

log = get_logger("migrate_task_status")

def run_migration():
    log.info("Starting task_status schema migration...")

    schema_sql = """
    CREATE TABLE IF NOT EXISTS task_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id VARCHAR(255) UNIQUE NOT NULL,
        task_type VARCHAR(100) NOT NULL,
        status VARCHAR(50) NOT NULL,
        retry_count INTEGER DEFAULT 0,
        failure_reason TEXT,
        payload TEXT,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Handle PostgreSQL AUTOINCREMENT difference
    if os.getenv("DATABASE_URL", "").startswith("postgre"):
        schema_sql = schema_sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")

    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_task_status_task_id ON task_status(task_id);",
        "CREATE INDEX IF NOT EXISTS idx_task_status_status ON task_status(status);"
    ]

    try:
        with get_db() as conn:
            conn.execute(schema_sql)
            for idx_sql in indexes_sql:
                conn.execute(idx_sql)
        log.info("task_status schema migration complete.")
    except Exception as e:
        log.error("Migration failed: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
