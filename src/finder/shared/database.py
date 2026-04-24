"""
src/finder/shared/database.py
-----------------------------
SQLite database initialization and connection management.
"""

import sqlite3
import os
from finder.shared.logger import get_logger
from finder.shared.config import DB_PATH

log = get_logger("db")

# Ensure data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_db() -> sqlite3.Connection:
    """
    Return a SQLite connection with WAL mode enabled.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    """
    Create all tables if they don't exist.
    """
    log.info(f"Initializing database: {DB_PATH}")
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT NOT NULL,
            company      TEXT NOT NULL,
            platform     TEXT NOT NULL,
            location     TEXT,
            description  TEXT,
            skills       TEXT,
            salary       TEXT,
            posted_at    TEXT,
            job_url      TEXT UNIQUE NOT NULL,
            form_type    TEXT DEFAULT 'unknown',
            scraped_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active    INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS apply_queue (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            job_url              TEXT UNIQUE,
            job_json             TEXT,
            status               TEXT DEFAULT 'pending',
            match_score_at_apply REAL,
            risk_score           REAL,
            goal_boost           REAL DEFAULT 1.0,
            attempts             INTEGER DEFAULT 0,
            is_exploration       INTEGER DEFAULT 0,
            last_error           TEXT,
            assistant_data       TEXT,
            relevance_feedback   TEXT,
            queued_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at           DATETIME
        );

        CREATE TABLE IF NOT EXISTS user_goals (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_type  TEXT,
            value      TEXT,
            priority   INTEGER DEFAULT 5,
            active     INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS goal_progress (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id       INTEGER REFERENCES user_goals(id),
            date          DATE DEFAULT CURRENT_DATE,
            current_value REAL DEFAULT 0,
            target_value  REAL,
            met           INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS application_outcomes (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            job_url          TEXT,
            job_title        TEXT,
            company          TEXT,
            platform         TEXT,
            match_score      REAL,
            outcome          TEXT,
            days_to_respond  INTEGER,
            notes            TEXT,
            recorded_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS skill_outcome_map (
            skill   TEXT,
            outcome TEXT,
            count   INTEGER DEFAULT 1,
            PRIMARY KEY (skill, outcome)
        );

        CREATE TABLE IF NOT EXISTS threshold_history (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            threshold    REAL,
            success_rate REAL,
            applied      INTEGER,
            failed       INTEGER,
            date         DATE DEFAULT CURRENT_DATE
        );

        CREATE TABLE IF NOT EXISTS failure_patterns (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            module      TEXT,
            error_type  TEXT,
            platform    TEXT,
            hour_of_day INTEGER,
            day_of_week INTEGER,
            count       INTEGER DEFAULT 1,
            last_seen   DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(module, error_type, platform, hour_of_day)
        );

        CREATE TABLE IF NOT EXISTS behavior_signals (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            job_url       TEXT,
            job_title     TEXT,
            job_skills    TEXT,
            action        TEXT,
            score_at_time REAL,
            timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS exploration_log (
            job_url          TEXT PRIMARY KEY,
            score_at_explore REAL,
            platform         TEXT,
            outcome          TEXT,
            created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS company_intelligence (
            company           TEXT PRIMARY KEY COLLATE NOCASE,
            tier              TEXT DEFAULT 'unknown',
            interview_rate    REAL DEFAULT 0.0,
            response_rate     REAL DEFAULT 0.0,
            total_applies     INTEGER DEFAULT 0,
            total_interviews  INTEGER DEFAULT 0,
            avg_response_days REAL DEFAULT 0,
            last_applied      DATE,
            notes             TEXT,
            updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS company_signals (
            company    TEXT PRIMARY KEY,
            signal     TEXT,
            reason     TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS apply_risk_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            platform   TEXT,
            job_url    TEXT,
            risk_score REAL,
            decision   TEXT,
            reason     TEXT,
            outcome    TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS application_confidence (
            job_url     TEXT PRIMARY KEY,
            confidence  REAL,
            trust_level TEXT,
            signals     TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_controls (
            key        TEXT PRIMARY KEY,
            value      TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS approval_queue (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            job_url    TEXT,
            job_title  TEXT,
            company    TEXT,
            trigger    TEXT,
            context    TEXT,
            status     TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            decided_at DATETIME
        );

        CREATE TABLE IF NOT EXISTS query_weights (
            query      TEXT PRIMARY KEY,
            weight     REAL DEFAULT 1.0,
            successes  INTEGER DEFAULT 0,
            skips      INTEGER DEFAULT 0,
            last_used  DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        # Migration: Add query_weights if missing
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_weights (
                query      TEXT PRIMARY KEY,
                weight     REAL DEFAULT 1.0,
                successes  INTEGER DEFAULT 0,
                skips      INTEGER DEFAULT 0,
                last_used  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Seed default queries
        defaults = [
            ('python developer', 0.8),
            ('backend developer', 0.7),
            ('automation tester', 0.5),
            ('software engineer', 0.6)
        ]
        for q, w in defaults:
            conn.execute("INSERT OR IGNORE INTO query_weights (query, weight) VALUES (?, ?)", (q, w))

        # Migration: Add assistant_data if missing
        try:
            conn.execute("ALTER TABLE apply_queue ADD COLUMN assistant_data TEXT")
        except sqlite3.OperationalError:
            pass # Column already exists
            
        try:
            conn.execute("ALTER TABLE apply_queue ADD COLUMN relevance_feedback TEXT")
        except sqlite3.OperationalError:
            pass

        # Performance: Add Indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_apply_status ON apply_queue(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_apply_score ON apply_queue(match_score_at_apply)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_apply_queued ON apply_queue(queued_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_scraped ON jobs(scraped_at)")

        # Cleanup: Remove potential duplicates (same URL in queue)
        conn.execute("""
            DELETE FROM apply_queue 
            WHERE id NOT IN (
                SELECT MIN(id) FROM apply_queue GROUP BY job_url
            )
        """)
        
        # Archive: Move jobs older than 30 days to a historical state or just clean up
        # For now, we'll just log or keep it simple.
        
    _insert_default_controls()
    log.info("Database initialized and optimized successfully")

def _insert_default_controls():
    defaults = {
        "paused":           "false",
        "aggressiveness":   "normal",
        "daily_cap":        "10",
        "weekly_cap":       "50",
        "min_match":        "70",
        "max_risk":         "0.6",
        "require_approval": "false",
        "explore_rate":     "0.15",
        "platforms":        '["internshala", "indeed"]',
    }
    with get_db() as conn:
        for key, value in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO user_controls (key, value) VALUES (?, ?)",
                (key, value),
            )

def get_table_counts() -> dict:
    tables = [
        "jobs", "apply_queue", "user_goals", "application_outcomes",
        "company_intelligence", "user_controls", "approval_queue",
    ]
    counts = {}
    with get_db() as conn:
        for table in tables:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            counts[table] = row[0]
    return counts
