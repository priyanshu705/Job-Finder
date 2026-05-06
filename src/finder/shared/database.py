"""
src/finder/shared/database.py
-----------------------------
AutoApply AI — Database connection manager.
Supports SQLite (dev) and PostgreSQL/Supabase (production).
"""

import os
import logging
from finder.shared.logger import get_logger

log = get_logger("db")

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Normalise postgres:// → postgresql:// (Render / Heroku emit the older scheme)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    os.environ["DATABASE_URL"] = DATABASE_URL  # keep env in sync

_USE_POSTGRES = DATABASE_URL.startswith("postgresql://")


# ── PostgreSQL helpers ─────────────────────────────────────────────────────────

if _USE_POSTGRES:
    import psycopg2
    import psycopg2.extras

    def _new_pg_conn():
        """Open a fresh psycopg2 dict-cursor connection."""
        return psycopg2.connect(
            DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor,
            connect_timeout=10,
        )

    def _pg_sql(sql: str) -> str:
        """Convert SQLite-style ? placeholders → %s for psycopg2."""
        return sql.replace("?", "%s")

    class _PGCursor:
        def __init__(self, cur):
            self._cur = cur

        def fetchall(self):
            try:
                return self._cur.fetchall() or []
            except Exception:
                return []

        def fetchone(self):
            try:
                return self._cur.fetchone()
            except Exception:
                return None

        @property
        def lastrowid(self):
            """
            psycopg2 doesn't populate lastrowid; callers that need the new PK
            must use RETURNING id in their SQL.  We try to fetch it here.
            """
            try:
                row = self._cur.fetchone()
                if row:
                    return row.get("id") or list(row.values())[0]
            except Exception:
                pass
            return None

    class _PGProxy:
        """Thin wrapper that makes psycopg2 feel like sqlite3 for our codebase."""

        def __init__(self, conn):
            self._conn = conn

        def execute(self, sql, params=()):
            sql = _pg_sql(sql)
            cur = self._conn.cursor()
            cur.execute(sql, params)
            return _PGCursor(cur)

        def executescript(self, sql):
            # executescript is SQLite-only; split and run each statement.
            cur = self._conn.cursor()
            for stmt in sql.split(";"):
                stmt = stmt.strip()
                if stmt:
                    try:
                        cur.execute(_pg_sql(stmt))
                    except Exception as e:
                        log.warning("executescript stmt skipped: %s", e)
                        self._conn.rollback()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    class _PGConn:
        """Context-manager that opens a connection and commits/rolls back."""

        def __enter__(self):
            self._conn = _new_pg_conn()
            self._conn.autocommit = False
            return _PGProxy(self._conn)

        def __exit__(self, exc_type, *_):
            if exc_type:
                try:
                    self._conn.rollback()
                except Exception:
                    pass
            else:
                try:
                    self._conn.commit()
                except Exception:
                    pass
            try:
                self._conn.close()
            except Exception:
                pass

    def get_db():
        return _PGConn()


# ── SQLite helpers ─────────────────────────────────────────────────────────────

else:
    import sqlite3
    from finder.shared.config import DB_PATH

    # Ensure data directory exists (only relevant in SQLite mode)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    def get_db():  # noqa: F811
        return _SQLiteConn()

    class _SQLiteConn:
        def __enter__(self):
            self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            return self._conn

        def __exit__(self, exc_type, *_):
            if exc_type:
                self._conn.rollback()
            else:
                self._conn.commit()
            self._conn.close()


# ── Schema initialization ──────────────────────────────────────────────────────

def _ddl(sql: str) -> str:
    """Adapt DDL for the active database backend."""
    if _USE_POSTGRES:
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        sql = sql.replace("DATETIME DEFAULT CURRENT_TIMESTAMP", "TIMESTAMP DEFAULT NOW()")
        sql = sql.replace("DATETIME", "TIMESTAMP")
        sql = sql.replace("DATE DEFAULT CURRENT_DATE", "DATE DEFAULT CURRENT_DATE")
        sql = sql.replace("COLLATE NOCASE", "")
    return sql


def init_db():
    """Create all tables if they don't exist. Safe to call multiple times."""
    log.info("Initializing database (postgres=%s)", _USE_POSTGRES)

    schema = """
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
            goal_id       INTEGER,
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
            last_seen   DATETIME DEFAULT CURRENT_TIMESTAMP
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
            company           TEXT PRIMARY KEY,
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

        CREATE TABLE IF NOT EXISTS resume_data (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filename    TEXT,
            raw_text    TEXT,
            skills      TEXT,
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """

    if _USE_POSTGRES:
        conn = _new_pg_conn()
        conn.autocommit = True
        cur = conn.cursor()
        adapted = _ddl(schema)
        for stmt in adapted.split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    cur.execute(stmt)
                except Exception as e:
                    log.warning("DDL skipped: %s", e)
        _pg_indexes(cur)
        conn.close()
    else:
        import sqlite3
        with get_db() as conn:
            conn.executescript(schema)
            # Safe migrations — add columns that may not exist yet
            for col_sql in [
                "ALTER TABLE apply_queue ADD COLUMN assistant_data TEXT",
                "ALTER TABLE apply_queue ADD COLUMN relevance_feedback TEXT",
            ]:
                try:
                    conn.execute(col_sql)
                except sqlite3.OperationalError:
                    pass  # Column already exists
            conn.execute("CREATE INDEX IF NOT EXISTS idx_apply_status ON apply_queue(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_apply_score  ON apply_queue(match_score_at_apply)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_apply_queued ON apply_queue(queued_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_scraped ON jobs(scraped_at)")
            # Deduplicate stale rows
            conn.execute("""
                DELETE FROM apply_queue
                WHERE id NOT IN (SELECT MIN(id) FROM apply_queue GROUP BY job_url)
            """)
            # Reset any stuck 'pending' jobs that already have a score (leftover from old bug)
            conn.execute("""
                UPDATE apply_queue
                SET status = 'ready_to_apply', updated_at = CURRENT_TIMESTAMP
                WHERE status = 'pending'
                  AND match_score_at_apply IS NOT NULL
            """)

    _insert_default_controls()
    _seed_query_weights()
    log.info("Database initialized successfully")


def _pg_indexes(cur):
    for ddl in [
        "CREATE INDEX IF NOT EXISTS idx_apply_status ON apply_queue(status)",
        "CREATE INDEX IF NOT EXISTS idx_apply_score  ON apply_queue(match_score_at_apply)",
        "CREATE INDEX IF NOT EXISTS idx_apply_queued ON apply_queue(queued_at)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_scraped ON jobs(scraped_at)",
    ]:
        try:
            cur.execute(ddl)
        except Exception:
            pass


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
    # Route through get_db() so _PGProxy handles ? → %s conversion for both backends
    with get_db() as conn:
        for key, value in defaults.items():
            try:
                if _USE_POSTGRES:
                    conn.execute(
                        "INSERT INTO user_controls (key, value) VALUES (?, ?) "
                        "ON CONFLICT (key) DO NOTHING",
                        (key, value),
                    )
                else:
                    conn.execute(
                        "INSERT OR IGNORE INTO user_controls (key, value) VALUES (?, ?)",
                        (key, value),
                    )
            except Exception as e:
                log.debug("Default control insert skipped (%s): %s", key, e)


def _seed_query_weights():
    defaults = [
        ("python developer",  0.8),
        ("backend developer", 0.7),
        ("automation tester", 0.5),
        ("software engineer", 0.6),
    ]
    with get_db() as conn:
        for q, w in defaults:
            try:
                if _USE_POSTGRES:
                    conn.execute(
                        "INSERT INTO query_weights (query, weight) VALUES (?, ?) "
                        "ON CONFLICT (query) DO NOTHING",
                        (q, w),
                    )
                else:
                    conn.execute(
                        "INSERT OR IGNORE INTO query_weights (query, weight) VALUES (?, ?)",
                        (q, w),
                    )
            except Exception as e:
                log.debug("Seed query_weights skipped (%s): %s", q, e)


def get_table_counts() -> dict:
    tables = [
        "jobs", "apply_queue", "user_goals", "application_outcomes",
        "company_intelligence", "user_controls", "approval_queue",
    ]
    counts = {}
    with get_db() as conn:
        for table in tables:
            try:
                row = conn.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()
                counts[table] = (row["c"] if row else 0)
            except Exception:
                counts[table] = -1
    return counts
