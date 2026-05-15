"""
Migration guide for adding multi-user support to existing AutoApply AI installation.
This handles data migration from single-user to multi-user architecture.
"""

import sqlite3
import os
import logging

log = logging.getLogger(__name__)

def migrate_to_multiuser():
    """
    Safely migrate existing single-user data to multi-user architecture.
    
    Steps:
    1. Create users table
    2. Create default admin user
    3. Add user_id to all tables
    4. Backfill existing data with admin user_id
    5. Add foreign key constraints
    
    This is safe to run multiple times (idempotent).
    """
    
    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
        log.info("Skipping sqlite migration in PostgreSQL mode")
        return False

    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "", 1)
    else:
        db_path = db_url or os.path.join("data", "finder.db")

    db_dir = os.path.dirname(os.path.abspath(db_path))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Step 1: Create users table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                is_active INTEGER DEFAULT 1
            )
        """)
        log.info("✓ Users table created")
        
        # Step 2: Create admin user if not exists
        cursor.execute("SELECT id FROM users WHERE email = ?", ("admin@autoapply.local",))
        admin = cursor.fetchone()
        
        if not admin:
            from werkzeug.security import generate_password_hash
            password_hash = generate_password_hash("change-me-in-production")
            cursor.execute(
                "INSERT INTO users (email, password_hash, full_name) VALUES (?, ?, ?)",
                ("admin@autoapply.local", password_hash, "Admin User")
            )
            admin_id = cursor.lastrowid
            log.info(f"✓ Admin user created (id={admin_id})")
        else:
            admin_id = admin[0]
            log.info(f"✓ Admin user already exists (id={admin_id})")
        
        conn.commit()
        
        # Step 3: Add user_id columns if not exists
        tables_to_migrate = [
            'jobs',
            'apply_queue',
            'user_goals',
            'application_outcomes',
            'skill_outcome_map',
            'threshold_history'
        ]
        
        for table in tables_to_migrate:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'user_id' not in columns:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER DEFAULT {admin_id}")
                log.info(f"✓ Added user_id to {table}")
            else:
                log.info(f"✓ user_id already exists in {table}")
        
        conn.commit()
        
        # Step 4: Add foreign key constraints
        # Note: SQLite doesn't support adding FK constraints after table creation
        # So we'll document the constraints in comments
        log.info("✓ Foreign key constraints documented (implement in schema redesign)")
        
        # Step 5: Create approval queue table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS approval_queue_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                job_url TEXT NOT NULL,
                job_json TEXT,
                ai_answers_json TEXT,
                match_score REAL,
                status TEXT DEFAULT 'pending',
                approved_at DATETIME,
                applied_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        log.info("✓ Approval queue table created")
        
        # Step 6: Create blacklist table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                company TEXT,
                reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        log.info("✓ Blacklist table created")
        
        # Step 7: Create AI cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE NOT NULL,
                prompt TEXT,
                context TEXT,
                response TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        log.info("✓ AI cache table created")
        
        conn.commit()
        log.info("✅ Multi-user migration complete!")
        
        return True
        
    except Exception as e:
        log.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate_to_multiuser()
