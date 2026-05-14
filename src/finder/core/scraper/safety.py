"""
src/finder/core/scraper/safety.py
---------------------------------
Phase D: Scraper Safety Layer
Implements rate limiting, cooldown tracking, and failure monitoring to prevent bans.
"""

import time
import logging
from datetime import datetime, timedelta
from finder.shared.database import get_db

log = logging.getLogger("scraper_safety")

class CooldownManager:
    """Manages cooldowns for specific scraper platforms to prevent aggressive polling."""
    
    @staticmethod
    def set_cooldown(platform: str, duration_minutes: int, reason: str):
        """Put a platform scraper into a cooldown state."""
        expires_at = (datetime.utcnow() + timedelta(minutes=duration_minutes)).isoformat()
        try:
            with get_db() as conn:
                key = f"cooldown_{platform}"
                val = f"{expires_at}|{reason}"
                
                if conn._conn.__class__.__name__ == "sqlite3.Connection": # SQLite fallback
                     conn.execute(
                        "INSERT OR REPLACE INTO user_controls (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                        (key, val)
                    )
                else: # Postgres fallback
                     conn.execute(
                        "INSERT INTO user_controls (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                        "ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP",
                        (key, val)
                    )
            log.warning(f"Platform {platform} placed on cooldown for {duration_minutes}m. Reason: {reason}")
            
            # Emit socket event for frontend observability
            from finder.api.sockets import emit_event
            emit_event("scraper:cooldown", {"platform": platform, "duration": duration_minutes, "reason": reason})
            
        except Exception as exc:
            log.error(f"Failed to set cooldown for {platform}: {exc}")

    @staticmethod
    def is_on_cooldown(platform: str) -> bool:
        """Check if a platform is currently in a cooldown state."""
        try:
            with get_db() as conn:
                key = f"cooldown_{platform}"
                row = conn.execute("SELECT value FROM user_controls WHERE key = ?", (key,)).fetchone()
                if row and row["value"]:
                    parts = row["value"].split("|")
                    if len(parts) >= 1:
                        expires_at = datetime.fromisoformat(parts[0])
                        if datetime.utcnow() < expires_at:
                            return True
        except Exception as exc:
            log.error(f"Failed to check cooldown for {platform}: {exc}")
        return False


class RateLimiter:
    """Simple rate limiter to inject safe artificial delays."""
    
    @staticmethod
    def wait_safe(min_seconds: float = 2.0, max_seconds: float = 5.0):
        """Wait a random duration within safe bounds to mimic human behavior."""
        import random
        duration = random.uniform(min_seconds, max_seconds)
        time.sleep(duration)
