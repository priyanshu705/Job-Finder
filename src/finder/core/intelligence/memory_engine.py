"""
src/finder/core/intelligence/memory_engine.py
---------------------------------------------
Phase F: Long-Term Memory Engine
Creates persistent behavioral intelligence by tracking approved/rejected jobs and modifying future recommendations.
"""

import logging
from typing import Dict
from finder.shared.database import get_db

log = logging.getLogger("memory_engine")

def record_behavior(user_id: int, event_type: str, context: str, weight: float = 1.0):
    """
    Record a behavioral event.
    Event types: 'approved', 'rejected', 'interview', 'ignored'
    Context: e.g., 'frontend', 'Python', 'Remote', 'Startup'
    """
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO user_behavior_memory (user_id, event_type, context, weight) VALUES (?, ?, ?, ?)",
                (user_id, event_type, context, weight)
            )
            log.info("Recorded behavior: %s -> %s", event_type, context)
    except Exception as exc:
        log.error("Failed to record behavior: %s", exc)

def get_preference_weights(user_id: int) -> Dict[str, float]:
    """
    Calculate dynamic preference weights based on historical behavior.
    Approvals boost the weight, rejections penalize it.
    Returns a dictionary of contexts to weight modifiers (e.g., {'Python': 1.2, 'React': 0.8})
    """
    preferences = {}
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT event_type, context, weight FROM user_behavior_memory WHERE user_id = ?",
                (user_id,)
            ).fetchall()
            
            for row in rows:
                ctx = row["context"].lower().strip()
                if ctx not in preferences:
                    preferences[ctx] = 1.0
                    
                if row["event_type"] in ("approved", "interview"):
                    preferences[ctx] += (0.1 * row["weight"])
                elif row["event_type"] in ("rejected", "ignored"):
                    preferences[ctx] -= (0.1 * row["weight"])
                    
        # Clamp preferences between 0.5 and 2.0 to prevent runaway biases
        for ctx in preferences:
            preferences[ctx] = max(0.5, min(2.0, preferences[ctx]))
            
    except Exception as exc:
        log.error("Failed to calculate preference weights: %s", exc)
        
    return preferences
