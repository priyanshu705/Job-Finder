import sqlite3
from datetime import datetime
from finder.shared.database import get_db
from finder.shared.logger import get_logger
from finder.core.intelligence.profile import detect_roles, get_user_skills

log = get_logger("adaptive_search")

def initialize_queries():
    """Seed the query_weights table based on detected roles."""
    skills = get_user_skills()
    roles = detect_roles(skills)
    
    with get_db() as conn:
        for role in roles:
            conn.execute(
                "INSERT OR IGNORE INTO query_weights (query, weight) VALUES (?, ?)",
                (role, 1.0)
            )

def get_weighted_queries(limit=3):
    """Get the top N queries based on weights and success history."""
    try:
        initialize_queries() # Ensure seeded
    except sqlite3.OperationalError:
        # Table might be missing, try to force init_db
        from finder.shared.database import init_db
        init_db()
        initialize_queries()
    
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT query, weight FROM query_weights 
            ORDER BY weight DESC, last_used ASC 
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        
    return [dict(r) for r in rows]

def update_query_weight(query: str, delta: float):
    """Adjust the weight of a query (e.g. +0.1 for apply, -0.2 for skip)."""
    with get_db() as conn:
        conn.execute(
            """
            UPDATE query_weights 
            SET weight = MAX(0.1, weight + ?), 
                last_used = CURRENT_TIMESTAMP 
            WHERE query = ?
            """,
            (delta, query)
        )
        # Record usage if delta is positive (means we applied)
        if delta > 0:
            conn.execute("UPDATE query_weights SET successes = successes + 1 WHERE query = ?", (query,))
        elif delta < 0:
            conn.execute("UPDATE query_weights SET skips = skips + 1 WHERE query = ?", (query,))

def record_feedback(query: str, success: bool):
    """External entry point for feedback loop."""
    delta = 0.1 if success else -0.05
    update_query_weight(query, delta)
    log.info(f"Adapted search weight for '{query}': {'boosted' if success else 'reduced'}")
