"""
src/finder/core/queue/service.py
---------------------------------
Queue ranking + assistant_data pre-generation — AutoApply AI.

Responsibilities:
  1. Promote any 'ready_to_apply' jobs that are missing assistant_data
     by calling generate_smart_answers() for each.
  2. Return a ranked batch of jobs for the apply assistant.
"""

import json
from finder.shared.database import get_db
from finder.shared.logger import get_logger
from finder.core.apply_bot.answer_generator import generate_smart_answers

log = get_logger("queue")


def run_queue() -> dict:
    """
    For every job in 'ready_to_apply' status that has no assistant_data,
    generate and persist AI answers so the assistant panel is populated.
    """
    stats = {"processed": 0, "assistant_generated": 0, "already_had_data": 0, "errors": 0}

    with get_db() as conn:
        jobs = [dict(r) for r in conn.execute(
            """
            SELECT q.id, q.job_url, q.match_score_at_apply, q.goal_boost, q.assistant_data,
                   j.title, j.company, j.skills, j.description
            FROM apply_queue q
            LEFT JOIN jobs j ON j.job_url = q.job_url
            WHERE q.status = 'ready_to_apply'
            ORDER BY q.goal_boost DESC NULLS LAST,
                     q.match_score_at_apply DESC NULLS LAST
            """
        ).fetchall()]

    log.info(f"Queue: found {len(jobs)} ready_to_apply jobs to process.")

    with get_db() as conn:
        for job in jobs:
            stats["processed"] += 1

            # Skip if assistant_data already populated
            if job.get("assistant_data"):
                try:
                    existing = json.loads(job["assistant_data"])
                    if existing.get("cover_letter") or existing.get("explanation"):
                        stats["already_had_data"] += 1
                        continue
                except Exception:
                    pass  # corrupted JSON — regenerate

            # Generate AI assistant data
            try:
                ai_data = generate_smart_answers(job)
                conn.execute(
                    "UPDATE apply_queue SET assistant_data=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (json.dumps(ai_data), job["id"])
                )
                stats["assistant_generated"] += 1
                log.debug(f"  ✅ Generated assistant data for: {job.get('title','?')} @ {job.get('company','?')}")
            except Exception as e:
                log.error(f"  ❌ Failed to generate assistant data for job id={job['id']}: {e}")
                stats["errors"] += 1

    log.info(
        f"Queue done: processed={stats['processed']} "
        f"generated={stats['assistant_generated']} "
        f"already_had={stats['already_had_data']} "
        f"errors={stats['errors']}"
    )
    return stats


def get_next_batch(n: int = 10, min_score: float = 0) -> list:
    """Get the next batch of ranked jobs ready for the apply assistant."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT q.id, q.job_url, q.match_score_at_apply, q.goal_boost, q.assistant_data,
                   j.title, j.company, j.skills
            FROM apply_queue q
            LEFT JOIN jobs j ON j.job_url = q.job_url
            WHERE q.status = 'ready_to_apply'
              AND (q.match_score_at_apply IS NULL OR q.match_score_at_apply >= ?)
            ORDER BY q.goal_boost DESC NULLS LAST,
                     q.match_score_at_apply DESC NULLS LAST
            LIMIT ?
            """,
            (min_score, n)
        ).fetchall()
    return [dict(r) for r in rows]
