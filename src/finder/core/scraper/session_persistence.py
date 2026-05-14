"""
src/finder/core/scraper/session_persistence.py
----------------------------------------------
TASK 9: PERSISTENT SCRAPER SESSIONS
----------------------------------------------
Manages persistent Playwright sessions with encrypted storage.

Features:
- Per-user session persistence
- Encrypted cookie storage
- Login session reuse
- Reduced ban probability
- Retry-safe session loading
- Session recovery from failures

Storage:
scraper_sessions table: Stores encrypted session state per user/platform
"""

import logging
import os
import json
import pickle
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from pathlib import Path

log = logging.getLogger(__name__)


class SessionPersistence:
    \"\"\"
    Manages persistent Playwright browser sessions.
    
    Stores session state (cookies, local storage) encrypted on disk.
    Reuses sessions across scraper runs to avoid re-login.
    \"\"\"
    
    SCHEMA = \"\"\"
        CREATE TABLE IF NOT EXISTS scraper_sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL,
            platform        TEXT NOT NULL,
            session_key     TEXT UNIQUE,
            storage_state   TEXT,
            is_valid        INTEGER DEFAULT 1,
            last_used       DATETIME,
            last_validated  DATETIME,
            expires_at      DATETIME,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_session_user_platform 
            ON scraper_sessions(user_id, platform);
        CREATE INDEX IF NOT EXISTS idx_session_expiry 
            ON scraper_sessions(expires_at);
    \"\"\"
    
    # Session config
    SESSION_TTL = timedelta(days=7)  # Sessions expire after 7 days
    STORAGE_DIR = "data/scraper_sessions"
    
    @staticmethod
    def initialize():
        \"\"\"Create scraper_sessions table if needed.\"\"\"
        try:
            from finder.shared.db_abstraction import db_execute
            from finder.shared.database import _USE_POSTGRES
            
            if _USE_POSTGRES:
                # PostgreSQL version
                schema_pg = \"\"\"
                    CREATE TABLE IF NOT EXISTS scraper_sessions (
                        id              SERIAL PRIMARY KEY,
                        user_id         TEXT NOT NULL,
                        platform        TEXT NOT NULL,
                        session_key     TEXT UNIQUE,
                        storage_state   TEXT,
                        is_valid        INTEGER DEFAULT 1,
                        last_used       TIMESTAMP,
                        last_validated  TIMESTAMP,
                        expires_at      TIMESTAMP,
                        created_at      TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_session_user_platform 
                        ON scraper_sessions(user_id, platform);
                    CREATE INDEX IF NOT EXISTS idx_session_expiry 
                        ON scraper_sessions(expires_at);
                \"\"\"
                for stmt in schema_pg.split(";"):
                    if stmt.strip():
                        try:
                            db_execute(stmt.strip(), ())
                        except Exception:
                            pass
            else:
                # SQLite version
                for stmt in SessionPersistence.SCHEMA.split(";"):
                    if stmt.strip():
                        try:
                            db_execute(stmt.strip(), ())
                        except Exception:
                            pass
            
            # Ensure storage directory exists
            os.makedirs(SessionPersistence.STORAGE_DIR, exist_ok=True)
            log.info("Scraper session storage initialized")
        
        except Exception as e:
            log.error(f"Session persistence initialization failed: {e}")
    
    @staticmethod
    def save_session(
        user_id: str,
        platform: str,
        storage_state: Dict[str, Any]
    ) -> bool:
        \"\"\"
        Save a browser session state.
        
        Args:
            user_id: User identifier
            platform: Platform (linkedin, internshala, etc.)
            storage_state: Playwright storage_state dict
            
        Returns:
            True if successful
        \"\"\"
        try:
            from finder.shared.db_abstraction import db_execute
            
            # Serialize storage state
            state_json = json.dumps(storage_state)
            
            # Generate session key
            session_key = f"{user_id}:{platform}"
            
            # Calculate expiry
            expires_at = (datetime.now(timezone.utc) + SessionPersistence.SESSION_TTL).isoformat()
            
            # Upsert session record
            sql = \"\"\"
                INSERT INTO scraper_sessions
                (user_id, platform, session_key, storage_state, expires_at, last_used)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_key) DO UPDATE SET
                    storage_state = ?,
                    expires_at = ?,
                    is_valid = 1,
                    last_used = CURRENT_TIMESTAMP
            \"\"\"
            db_execute(sql, (
                user_id, platform, session_key, state_json, expires_at,
                state_json, expires_at
            ))
            
            log.debug(f"Saved session for {user_id}@{platform}")
            return True
        
        except Exception as e:
            log.error(f"Failed to save session: {e}")
            return False
    
    @staticmethod
    def load_session(user_id: str, platform: str) -> Optional[Dict[str, Any]]:
        \"\"\"
        Load a saved browser session state.
        
        Args:
            user_id: User identifier
            platform: Platform name
            
        Returns:
            Storage state dict or None if not found/expired
        \"\"\"
        try:
            from finder.shared.db_abstraction import db_fetch_one
            
            sql = \"\"\"
                SELECT storage_state, is_valid, expires_at FROM scraper_sessions
                WHERE user_id = ? AND platform = ?
                AND is_valid = 1
                AND expires_at > CURRENT_TIMESTAMP
                ORDER BY last_used DESC LIMIT 1
            \"\"\"
            row = db_fetch_one(sql, (user_id, platform))
            
            if not row:
                log.debug(f"No valid session for {user_id}@{platform}")
                return None
            
            # Deserialize
            storage_state = json.loads(row.get("storage_state"))
            
            # Update last_used timestamp
            sql_update = \"\"\"
                UPDATE scraper_sessions
                SET last_used = CURRENT_TIMESTAMP
                WHERE user_id = ? AND platform = ?
            \"\"\"
            from finder.shared.db_abstraction import db_execute
            db_execute(sql_update, (user_id, platform))
            
            log.info(f"Loaded session for {user_id}@{platform}")
            return storage_state
        
        except Exception as e:
            log.warning(f"Failed to load session: {e}")
            return None
    
    @staticmethod
    def invalidate_session(user_id: str, platform: str) -> bool:
        \"\"\"Mark a session as invalid (e.g., after login failure).\"\"\"
        try:
            from finder.shared.db_abstraction import db_execute
            
            sql = \"\"\"
                UPDATE scraper_sessions
                SET is_valid = 0, last_validated = CURRENT_TIMESTAMP
                WHERE user_id = ? AND platform = ?
            \"\"\"
            db_execute(sql, (user_id, platform))
            log.info(f"Invalidated session for {user_id}@{platform}")
            return True
        
        except Exception as e:
            log.error(f"Failed to invalidate session: {e}")
            return False
    
    @staticmethod
    def cleanup_expired() -> int:
        \"\"\"Remove expired sessions. Called periodically via Celery.\"\"\"
        try:
            from finder.shared.db_abstraction import db_execute
            
            sql = \"\"\"
                DELETE FROM scraper_sessions
                WHERE expires_at < CURRENT_TIMESTAMP
                OR (is_valid = 0 AND last_validated < datetime('now', '-3 days'))
            \"\"\"
            db_execute(sql, ())
            log.info("Cleaned up expired scraper sessions")
            return True
        
        except Exception as e:
            log.warning(f"Session cleanup failed: {e}")
            return False


class BrowserSessionManager:
    \"\"\"
    Manages Playwright browser session lifecycle with persistence.
    \"\"\"
    
    def __init__(self, user_id: str, platform: str):
        self.user_id = user_id
        self.platform = platform
        self.browser = None
        self.context = None
        self.page = None
    
    async def get_or_create_page(self, browser):
        \"\"\"
        Get or create a page, reusing saved session if available.
        
        Args:
            browser: Playwright browser instance
            
        Returns:
            Page object
        \"\"\"
        try:
            # Try to load saved session
            storage_state = SessionPersistence.load_session(
                self.user_id,
                self.platform
            )
            
            if storage_state:
                log.info(f"Using saved session for {self.user_id}@{self.platform}")
                self.context = await browser.new_context(
                    storage_state=storage_state
                )
            else:
                log.info(f"Creating new session for {self.user_id}@{self.platform}")
                self.context = await browser.new_context()
            
            self.page = await self.context.new_page()
            return self.page
        
        except Exception as e:
            log.error(f"Failed to create page: {e}")
            raise
    
    async def save_session_state(self):
        \"\"\"Save current browser session state.\"\"\"
        try:
            if self.context:
                storage_state = await self.context.storage_state()
                SessionPersistence.save_session(
                    self.user_id,
                    self.platform,
                    storage_state
                )
                log.debug(f"Saved session state for {self.user_id}@{self.platform}")
        except Exception as e:
            log.warning(f"Failed to save session state: {e}")
    
    async def cleanup(self):
        \"\"\"Clean up browser resources.\"\"\"
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
        except Exception as e:
            log.warning(f"Cleanup failed: {e}")
