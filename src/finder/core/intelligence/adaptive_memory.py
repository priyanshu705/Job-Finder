"""
src/finder/core/intelligence/adaptive_memory.py
-----------------------------------------------
Phase C: Adaptive Ranking Memory
Learns from user actions (approve/reject/skip) without expensive ML models.
Applies rule-based or heuristic modifiers to future job scores.
"""

import logging
from finder.shared.database import get_db

log = logging.getLogger("adaptive_memory")

def record_action(job_url: str, action: str, job_title: str = "", job_skills: str = ""):
    """
    Record user behavior (approve, reject, skip) for adaptive memory.
    """
    try:
        with get_db() as conn:
            # We already have a behavior_signals table in the schema
            conn.execute(
                "INSERT INTO behavior_signals (job_url, job_title, job_skills, action) VALUES (?, ?, ?, ?)",
                (job_url, job_title, job_skills, action)
            )
    except Exception as exc:
        log.warning("Failed to record behavior signal: %s", exc)


def get_adaptive_modifiers(job_title: str) -> tuple[float, list[str]]:
    """
    Look up past behavior signals to adjust the score of a new job.
    E.g. If user rejected many jobs with "HR" in the title, apply a penalty.
    """
    if not job_title:
        return 0.0, []

    modifier = 0.0
    reasons = []
    title_lower = job_title.lower()

    try:
        with get_db() as conn:
            # Fetch recent rejection and approval signals
            # This is a very lightweight heuristic: count recent approvals and rejections of similar titles
            signals = conn.execute(
                "SELECT job_title, action FROM behavior_signals ORDER BY timestamp DESC LIMIT 100"
            ).fetchall()

            rejects = 0
            approvals = 0

            for sig in signals:
                past_title = (sig["job_title"] or "").lower()
                if not past_title:
                    continue
                
                # Simple keyword overlap heuristic for adaptive memory
                overlap = len(set(title_lower.split()) & set(past_title.split()))
                if overlap >= 2 or title_lower in past_title or past_title in title_lower:
                    if sig["action"] == "reject":
                        rejects += 1
                    elif sig["action"] == "approve":
                        approvals += 1

            if rejects >= 3 and approvals == 0:
                modifier -= 15.0
                reasons.append("Adaptive Memory: Reduced score because you consistently rejected similar roles recently")
            elif approvals >= 2 and rejects == 0:
                modifier += 10.0
                reasons.append("Adaptive Memory: Boosted score because you recently approved similar roles")

    except Exception as exc:
        log.warning("Failed to compute adaptive modifiers: %s", exc)

    return modifier, reasons
