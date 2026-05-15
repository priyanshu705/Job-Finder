"""
src/finder/core/scraper/session_manager.py
------------------------------------------
Phase D: Encrypted Session Persistence
Uses cryptography.fernet to securely store Playwright storage_state (cookies/tokens).
Prevents constant re-logins and protects session artifacts.
"""

import os
import json
import logging
from cryptography.fernet import Fernet
from finder.shared.database import get_db

log = logging.getLogger("session_manager")

# Ensure a secure encryption key is present, fallback to generating one if in dev
_SECRET = os.getenv("SESSION_SECRET_KEY")
if not _SECRET:
    _SECRET = Fernet.generate_key().decode('utf-8')
    os.environ["SESSION_SECRET_KEY"] = _SECRET
    log.warning("SESSION_SECRET_KEY not set. Generated ephemeral key. Sessions will invalidate on restart.")

fernet = Fernet(_SECRET.encode('utf-8'))

def save_encrypted_session(user_id: int, platform: str, storage_state: dict):
    """Encrypt and persist the Playwright storage_state for a user/platform."""
    try:
        raw_json = json.dumps(storage_state).encode('utf-8')
        encrypted_data = fernet.encrypt(raw_json).decode('utf-8')
        
        with get_db() as conn:
            # We'll use the user_controls table for quick key-value persistence
            key = f"session_{platform}_{user_id}"
            
            # Use appropriate upsert depending on backend
            if os.getenv("DATABASE_URL", "").startswith("postgresql://"):
                conn.execute(
                    "INSERT INTO user_controls (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                    "ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP",
                    (key, encrypted_data)
                )
            else:
                conn.execute(
                    "INSERT OR REPLACE INTO user_controls (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    (key, encrypted_data)
                )
        log.info(f"Encrypted session saved for user {user_id} on {platform}")
    except Exception as exc:
        log.error(f"Failed to encrypt and save session: {exc}")

def load_encrypted_session(user_id: int, platform: str) -> dict:
    """Retrieve and decrypt the Playwright storage_state."""
    try:
        key = f"session_{platform}_{user_id}"
        with get_db() as conn:
            row = conn.execute("SELECT value FROM user_controls WHERE key = ?", (key,)).fetchone()
            if row and row["value"]:
                encrypted_data = row["value"].encode('utf-8')
                raw_json = fernet.decrypt(encrypted_data).decode('utf-8')
                return json.loads(raw_json)
    except Exception as exc:
        log.warning(f"No valid encrypted session found for {platform}: {exc}")
    
    return {}
