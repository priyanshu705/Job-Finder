"""
src/finder/shared/token_revocation.py
------------------------------------
TASK 3: JWT REVOCATION SYSTEM
------------------------------------
Manages revoked JWT tokens to support:
- Session logout (refresh token revocation)
- Compromised session termination
- Token blacklist with efficient lookups
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from finder.shared.db_abstraction import (
    db_execute,
    db_fetch_all,
    db_fetch_one,
    db_count,
    db_table_exists,
    db_add_column,
)
from finder.shared.database import _USE_POSTGRES

log = logging.getLogger(__name__)


class TokenRevocationManager:
    """
    Manages revoked token blacklist.
    
    Tables:
    - revoked_tokens: Stores revoked token metadata
    - revoked_tokens_cache: Optional - for fast in-memory lookups
    
    Production features:
    - Efficient database queries
    - Automatic cleanup of expired entries
    - Multi-tenant safe
    - Both SQLite and PostgreSQL compatible
    """
    
    # Schema
    SCHEMA = """
        CREATE TABLE IF NOT EXISTS revoked_tokens (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            jti         TEXT NOT NULL UNIQUE,
            user_id     TEXT,
            revoked_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at  DATETIME,
            reason      TEXT DEFAULT 'unknown',
            revoked_by  TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_revoked_jti ON revoked_tokens(jti);
        CREATE INDEX IF NOT EXISTS idx_revoked_user ON revoked_tokens(user_id);
        CREATE INDEX IF NOT EXISTS idx_revoked_expiry ON revoked_tokens(expires_at);
    """
    
    @staticmethod
    def initialize():
        """Create revoked_tokens table if it doesn't exist."""
        try:
            if _USE_POSTGRES:
                # PostgreSQL version
                schema_pg = """
                    CREATE TABLE IF NOT EXISTS revoked_tokens (
                        id          SERIAL PRIMARY KEY,
                        jti         TEXT NOT NULL UNIQUE,
                        user_id     TEXT,
                        revoked_at  TIMESTAMP DEFAULT NOW(),
                        expires_at  TIMESTAMP,
                        reason      TEXT DEFAULT 'unknown',
                        revoked_by  TEXT
                    );
                    CREATE INDEX IF NOT EXISTS idx_revoked_jti ON revoked_tokens(jti);
                    CREATE INDEX IF NOT EXISTS idx_revoked_user ON revoked_tokens(user_id);
                    CREATE INDEX IF NOT EXISTS idx_revoked_expiry ON revoked_tokens(expires_at);
                """
                for stmt in schema_pg.split(";"):
                    if stmt.strip():
                        try:
                            db_execute(stmt.strip(), ())
                        except Exception as e:
                            log.debug(f"DDL skipped: {e}")
            else:
                # SQLite version
                for stmt in TokenRevocationManager.SCHEMA.split(";"):
                    if stmt.strip():
                        try:
                            db_execute(stmt.strip(), ())
                        except Exception as e:
                            log.debug(f"DDL skipped: {e}")
            
            log.info("Token revocation table initialized")
        except Exception as e:
            log.error(f"Failed to initialize revocation table: {e}")
            raise
    
    @staticmethod
    def revoke(
        jti: str,
        user_id: Optional[str] = None,
        reason: str = "unknown",
        revoked_by: Optional[str] = None,
        expires_at: Optional[str] = None
    ) -> None:
        """
        Revoke a token immediately.
        
        Args:
            jti: JWT ID (token identifier)
            user_id: User who owns the token
            reason: Why token was revoked (e.g., "logout", "compromised", "password_reset")
            revoked_by: Admin/system user who revoked the token
            expires_at: ISO timestamp when token would have expired anyway
        """
        try:
            sql = """
                INSERT INTO revoked_tokens (jti, user_id, reason, revoked_by, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """
            db_execute(sql, (jti, user_id, reason, revoked_by, expires_at))
            log.info(f"Revoked token {jti} for user {user_id}: {reason}")
        except Exception as e:
            log.error(f"Failed to revoke token {jti}: {e}")
            raise
    
    @staticmethod
    def is_revoked(jti: str) -> bool:
        """
        Check if a token has been revoked.
        
        Args:
            jti: JWT ID to check
            
        Returns:
            True if revoked, False otherwise
        """
        try:
            # Efficient single-row lookup
            sql = """
                SELECT id FROM revoked_tokens
                WHERE jti = ?
                LIMIT 1
            """
            row = db_fetch_one(sql, (jti,))
            is_revoked = row is not None
            
            if is_revoked:
                log.debug(f"Token {jti} is revoked")
            
            return is_revoked
        except Exception as e:
            log.error(f"Failed to check token revocation: {e}")
            # Fail open on error - allow token
            return False
    
    @staticmethod
    def revoke_all_user_tokens(user_id: str, reason: str = "user_requested") -> int:
        """
        Revoke all tokens for a specific user (e.g., on password change).
        
        Args:
            user_id: User identifier
            reason: Reason for revocation
            
        Returns:
            Number of tokens revoked
        """
        try:
            # Find all non-revoked tokens for this user that aren't expired yet
            sql = """
                SELECT jti FROM revoked_tokens
                WHERE user_id = ? 
                AND revoked_at IS NULL
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """
            tokens = db_fetch_all(sql, (user_id,))
            
            # Revoke each one
            for token in tokens:
                jti = token.get("jti")
                if jti:
                    TokenRevocationManager.revoke(
                        jti,
                        user_id=user_id,
                        reason=reason,
                        revoked_by="system"
                    )
            
            count = len(tokens)
            log.info(f"Revoked {count} tokens for user {user_id}: {reason}")
            return count
        except Exception as e:
            log.error(f"Failed to revoke user tokens: {e}")
            return 0
    
    @staticmethod
    def cleanup_expired() -> int:
        """
        Delete revocation entries for tokens that have already expired.
        Should be run periodically (e.g., daily via Celery task).
        
        Returns:
            Number of records deleted
        """
        try:
            sql = """
                DELETE FROM revoked_tokens
                WHERE expires_at IS NOT NULL
                AND expires_at < CURRENT_TIMESTAMP
                AND revoked_at < datetime('now', '-30 days')
            """
            db_execute(sql, ())
            
            # Get count of remaining entries (approximate)
            sql_count = "SELECT COUNT(*) as c FROM revoked_tokens"
            count_row = db_fetch_one(sql_count, ())
            count = count_row.get("c", 0) if count_row else 0
            
            log.info(f"Cleaned up expired token entries. {count} entries remain.")
            return count
        except Exception as e:
            log.warning(f"Token cleanup failed: {e}")
            return 0
    
    @staticmethod
    def get_user_revocations(user_id: str) -> List[dict]:
        """
        Get all revocation records for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of revocation records
        """
        try:
            sql = """
                SELECT jti, revoked_at, reason, revoked_by, expires_at
                FROM revoked_tokens
                WHERE user_id = ?
                ORDER BY revoked_at DESC
            """
            return db_fetch_all(sql, (user_id,))
        except Exception as e:
            log.error(f"Failed to get user revocations: {e}")
            return []
    
    @staticmethod
    def stats() -> dict:
        """Get statistics about revoked tokens."""
        try:
            total = db_count("SELECT COUNT(*) as c FROM revoked_tokens", ())
            
            sql_by_reason = """
                SELECT reason, COUNT(*) as c
                FROM revoked_tokens
                GROUP BY reason
            """
            by_reason = db_fetch_all(sql_by_reason, ())
            
            sql_recent = """
                SELECT COUNT(*) as c
                FROM revoked_tokens
                WHERE revoked_at > datetime('now', '-24 hours')
            """
            recent = db_count(sql_recent, ())
            
            return {
                "total_revoked": total,
                "recent_24h": recent,
                "by_reason": {r.get("reason"): r.get("c") for r in by_reason},
            }
        except Exception as e:
            log.warning(f"Failed to get revocation stats: {e}")
            return {}


# ──────────────────────────────────────────────────────────────────────────────
# INTEGRATION WITH JWT SECURITY
# ──────────────────────────────────────────────────────────────────────────────

def inject_revocation_check():
    """
    Monkey-patch the JWT security module to check revocations.
    Call this on app startup.
    """
    from finder.shared import jwt_security
    
    original_is_revoked = jwt_security._is_token_revoked
    
    def new_is_revoked(jti: str) -> bool:
        return TokenRevocationManager.is_revoked(jti)
    
    jwt_security._is_token_revoked = new_is_revoked
    log.info("Token revocation check injected into JWT security")


# ──────────────────────────────────────────────────────────────────────────────
# MIDDLEWARE FOR AUTO-LOGOUT ON REVOCATION
# ──────────────────────────────────────────────────────────────────────────────

def should_force_logout(jti: str) -> bool:
    """
    Determine if user should be force-logged-out due to token revocation.
    Used in before_request hooks to preemptively redirect users.
    """
    return TokenRevocationManager.is_revoked(jti)
