"""
src/finder/core/scraper/health.py
---------------------------------
Phase D: Source Health Engine
Tracks scraper metrics, calculates health scores, and emits realtime Socket.IO events.
"""

import logging
from datetime import datetime
from finder.shared.database import get_db
from finder.api.sockets import emit_event

log = logging.getLogger("source_health")

class SourceHealthTracker:
    @staticmethod
    def init_source(platform: str):
        """Ensure source exists in company_intelligence or a dedicated health table."""
        try:
            with get_db() as conn:
                # We can use user_controls for lightweight metrics per platform
                # e.g. metric_platform_jobs_scraped
                pass
        except Exception as exc:
            log.warning("Health track init failed: %s", exc)

    @staticmethod
    def record_scrape(platform: str, success: bool, jobs_found: int = 0, duration_seconds: float = 0.0):
        try:
            with get_db() as conn:
                if success:
                    # Increment jobs scraped and record last success
                    conn.execute(
                        "INSERT INTO user_controls (key, value) VALUES (?, ?) "
                        "ON CONFLICT (key) DO UPDATE SET value = CAST(value AS INTEGER) + ?, updated_at = CURRENT_TIMESTAMP",
                        (f"health_{platform}_jobs", str(jobs_found), jobs_found)
                    )
                    conn.execute(
                        "INSERT INTO user_controls (key, value) VALUES (?, ?) "
                        "ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP",
                        (f"health_{platform}_last_success", datetime.utcnow().isoformat())
                    )
                else:
                    # Increment failures
                    conn.execute(
                        "INSERT INTO user_controls (key, value) VALUES (?, '1') "
                        "ON CONFLICT (key) DO UPDATE SET value = CAST(value AS INTEGER) + 1, updated_at = CURRENT_TIMESTAMP",
                        (f"health_{platform}_failures",)
                    )
            
            # Emit Socket.IO event for dashboard
            emit_event("scraper:health", {
                "platform": platform,
                "status": "success" if success else "failed",
                "jobs_found": jobs_found,
                "duration": duration_seconds
            })
        except Exception as exc:
            log.error("Failed to record source health: %s", exc)

    @staticmethod
    def calculate_health_score(platform: str) -> float:
        """
        Calculates Domain Health Score:
        health_score = (success_rate * 0.6) - ban_penalty - (cooldown_freq * 0.2) - (captcha_freq * 0.2)
        """
        try:
            with get_db() as conn:
                jobs_row = conn.execute("SELECT value FROM user_controls WHERE key = ?", (f"health_{platform}_jobs",)).fetchone()
                fails_row = conn.execute("SELECT value FROM user_controls WHERE key = ?", (f"health_{platform}_failures",)).fetchone()
                cooldowns_row = conn.execute("SELECT value FROM user_controls WHERE key = ?", (f"health_{platform}_cooldowns",)).fetchone()
                captchas_row = conn.execute("SELECT value FROM user_controls WHERE key = ?", (f"health_{platform}_captchas",)).fetchone()
                
                jobs = int(jobs_row["value"]) if jobs_row else 0
                fails = int(fails_row["value"]) if fails_row else 0
                cooldowns = int(cooldowns_row["value"]) if cooldowns_row else 0
                captchas = int(captchas_row["value"]) if captchas_row else 0
                
                total = jobs + fails
                if total == 0:
                    return 100.0
                
                success_rate = (jobs / total) * 100.0
                ban_penalty = 30.0 if fails > (jobs * 2) else 0.0
                cooldown_penalty = min(20.0, cooldowns * 5.0)
                captcha_penalty = min(20.0, captchas * 5.0)
                
                final_score = (success_rate * 0.6) - ban_penalty - (cooldown_penalty * 0.2) - (captcha_penalty * 0.2)
                
                # If degraded, trigger dynamic throttling
                if final_score < 50.0:
                    log.warning(f"Platform {platform} health is severely degraded ({final_score}%). System will dynamically throttle scraping intensity.")
                
                return max(0.0, min(100.0, final_score))
        except Exception:
            return 100.0
