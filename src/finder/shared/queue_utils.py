"""
src/finder/shared/queue_utils.py
--------------------------------
Queue utilities, like resetting active queue elements after resume updates.
"""
from finder.shared.database import get_db, transaction
from finder.shared.logging import get_logger

log = get_logger("queue_utils")

def reset_active_queue(reason: str = "resume_updated") -> int:
    """
    Transaction-safe queue reset.
    Resets active apply_queue items (pending, ready_to_apply) so they are
    re-matched with the updated resume. Preserves applied/failed jobs.
    """
    sql = """
        UPDATE apply_queue 
        SET match_score_at_apply = NULL, 
            status = 'pending', 
            updated_at = CURRENT_TIMESTAMP,
            last_error = ?
        WHERE status IN ('pending', 'ready_to_apply')
    """
    with transaction() as conn:
        res = conn.execute(sql, (f"Reset Reason: {reason}",))
        count = res.rowcount if hasattr(res, 'rowcount') else 0
        log.info("Queue reset complete", extra={"reset_reason": reason, "reset_count": count})
        return count
