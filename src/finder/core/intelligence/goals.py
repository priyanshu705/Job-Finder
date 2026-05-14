"""
src/finder/core/intelligence/goals.py
-------------------------------------
Phase C: Goal Tracking System
Fetches user goals from the database to personalize ranking and behavior.
"""

import logging
from finder.shared.database import get_db

log = logging.getLogger("goals")

def get_user_goals(user_id: int = 1) -> dict:
    """
    Fetch all active goals for a user.
    Returns a dictionary of goal_type -> value.
    """
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT goal_type, value FROM user_goals WHERE user_id = ? AND active = 1",
                (user_id,)
            ).fetchall()
            
            goals = {}
            for row in rows:
                gtype = row["goal_type"]
                val = row["value"]
                # If multiple values exist for the same goal type, we could use a list, 
                # but for simplicity we assume the latest active one overrides or they are comma-separated.
                # Let's support lists for roles/companies:
                if gtype in goals:
                    if isinstance(goals[gtype], list):
                        goals[gtype].append(val)
                    else:
                        goals[gtype] = [goals[gtype], val]
                else:
                    if gtype in ('target_role', 'target_company', 'preferred_tech'):
                        goals[gtype] = [val]
                    else:
                        goals[gtype] = val
                        
            return goals
    except Exception as exc:
        log.warning("Failed to fetch user goals: %s", exc)
        return {}


def set_user_goal(user_id: int, goal_type: str, value: str, priority: int = 5):
    """Upserts a user goal."""
    try:
        with get_db() as conn:
            # Simple upsert logic
            conn.execute(
                "DELETE FROM user_goals WHERE user_id = ? AND goal_type = ?",
                (user_id, goal_type)
            )
            conn.execute(
                "INSERT INTO user_goals (user_id, goal_type, value, priority, active) VALUES (?, ?, ?, ?, 1)",
                (user_id, goal_type, value, priority)
            )
    except Exception as exc:
        log.error("Failed to set user goal %s: %s", goal_type, exc)
