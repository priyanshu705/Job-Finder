"""
src/finder/core/tasks/cleanup_tasks.py
--------------------------------------
Phase E: Cache TTL & Cleanup System
Prevents database bloat by cleaning up expired embeddings, AI generations,
read notifications, and old scrape snapshots.
"""

import logging
from datetime import datetime, timedelta
from finder.shared.celery_app import celery_app
from finder.shared.database import get_db

log = logging.getLogger("cleanup_tasks")

@celery_app.task(bind=True, max_retries=1)
def task_cleanup_cache(self):
    """
    Periodic task to clean up old data to protect Render free-tier storage limits.
    Run this nightly.
    """
    log.info("Starting scheduled cache cleanup...")
    
    try:
        with get_db() as conn:
            # 1. Clean up old embeddings (e.g., jobs older than 30 days)
            # Embeddings without an active job reference can be dropped.
            thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
            conn.execute(
                "DELETE FROM embedding_cache WHERE source_type = 'job' AND created_at < ?",
                (thirty_days_ago,)
            )
            
            # 2. Clean up old notifications (e.g., read notifications older than 7 days)
            seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            conn.execute(
                "DELETE FROM notifications WHERE read_status = 1 AND created_at < ?",
                (seven_days_ago,)
            )
            
            # 3. Clean up scrape snapshots older than 14 days
            fourteen_days_ago = (datetime.utcnow() - timedelta(days=14)).isoformat()
            conn.execute(
                "DELETE FROM user_controls WHERE key LIKE 'snapshot_%' AND updated_at < ?",
                (fourteen_days_ago,)
            )
            
        log.info("Cache cleanup completed successfully.")
        return True
    except Exception as exc:
        log.error("Failed to clean up cache: %s", exc)
        return False
