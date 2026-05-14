"""
src/finder/core/scraper/snapshots.py
------------------------------------
Phase D: Scrape Snapshot Storage
Stores lightweight metadata about a scrape for DOM change detection
and selector debugging.
"""

import logging
import hashlib
from datetime import datetime
from finder.shared.database import get_db

log = logging.getLogger("snapshots")

def save_snapshot(platform: str, html_content: str, selector_version: str = "v1"):
    """
    Store a hash of the HTML content to detect silent DOM changes.
    """
    if not html_content:
        return

    try:
        html_hash = hashlib.md5(html_content.encode('utf-8')).hexdigest()
        
        with get_db() as conn:
            key = f"snapshot_{platform}"
            val = f"{html_hash}|{datetime.utcnow().isoformat()}|{selector_version}"
            
            # Simple upsert
            conn.execute(
                "DELETE FROM user_controls WHERE key = ?",
                (key,)
            )
            conn.execute(
                "INSERT INTO user_controls (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (key, val)
            )
        log.debug(f"Saved snapshot for {platform} (Hash: {html_hash})")
    except Exception as exc:
        log.warning(f"Failed to save scrape snapshot: {exc}")
