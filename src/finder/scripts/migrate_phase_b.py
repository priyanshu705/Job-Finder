"""
src/finder/scripts/migrate_phase_b.py
--------------------------------------
Migration script to add tables for Phase B: AI Upgrade Layer.
"""

import logging
from finder.shared.database import get_db, _USE_POSTGRES, _ddl

log = logging.getLogger(__name__)

def migrate_phase_b():
    log.info("Starting Phase B database migration...")
    
    schema = """
        CREATE TABLE IF NOT EXISTS ai_generations (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            generation_type  TEXT NOT NULL,
            prompt_hash      TEXT NOT NULL,
            provider         TEXT DEFAULT 'gemini',
            response         TEXT,
            usage_count      INTEGER DEFAULT 1,
            created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS analytics_snapshots (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name   TEXT NOT NULL,
            metric_value  REAL,
            dimension     TEXT,
            snapshot_date DATE DEFAULT CURRENT_DATE
        );

        CREATE TABLE IF NOT EXISTS followup_queue (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            job_url       TEXT NOT NULL,
            type          TEXT NOT NULL, -- interview, recruiter, networking, recovery
            draft_content TEXT,
            status        TEXT DEFAULT 'draft', -- draft, approved, dismissed
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at    DATETIME
        );
        
        CREATE INDEX IF NOT EXISTS idx_ai_prompt_hash ON ai_generations(prompt_hash);
        CREATE INDEX IF NOT EXISTS idx_followup_status ON followup_queue(status);
        CREATE INDEX IF NOT EXISTS idx_analytics_date ON analytics_snapshots(snapshot_date);
    """

    try:
        with get_db() as conn:
            if _USE_POSTGRES:
                # DDL adaptation for Postgres is handled by _ddl if we were in init_db, 
                # but here we manually split and run.
                adapted = _ddl(schema)
                for stmt in adapted.split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        conn.execute(stmt)
            else:
                conn.executescript(schema)
        log.info("Phase B migration completed successfully.")
    except Exception as e:
        log.error(f"Phase B migration failed: {e}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate_phase_b()
