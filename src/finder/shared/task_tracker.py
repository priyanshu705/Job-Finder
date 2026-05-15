"""
src/finder/shared/task_tracker.py
---------------------------------
Utilities to manage the lifecycle of background tasks in the database.
"""
from finder.shared.database import transaction
from finder.shared.logging import get_logger

log = get_logger("task_tracker")

def create_task_record(task_id: str, task_type: str, payload: str = None):
    try:
        with transaction() as conn:
            conn.execute("""
                INSERT INTO task_status (task_id, task_type, status, payload)
                VALUES (?, ?, 'queued', ?)
            """, (task_id, task_type, payload))
    except Exception as e:
        log.error("Failed to create task record %s: %s", task_id, e)

def update_task_status(task_id: str, status: str, retry_count: int = 0):
    try:
        with transaction() as conn:
            if status == 'running':
                conn.execute("""
                    UPDATE task_status 
                    SET status = ?, started_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP, retry_count = ?
                    WHERE task_id = ?
                """, (status, retry_count, task_id))
            else:
                conn.execute("""
                    UPDATE task_status 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP, retry_count = ?
                    WHERE task_id = ?
                """, (status, retry_count, task_id))
    except Exception as e:
        log.error("Failed to update task status %s: %s", task_id, e)

def mark_task_failed(task_id: str, failure_reason: str):
    try:
        with transaction() as conn:
            conn.execute("""
                UPDATE task_status 
                SET status = 'failed', failure_reason = ?, completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """, (failure_reason, task_id))
    except Exception as e:
        log.error("Failed to mark task %s as failed: %s", task_id, e)

def mark_task_completed(task_id: str):
    try:
        with transaction() as conn:
            conn.execute("""
                UPDATE task_status 
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """, (task_id,))
    except Exception as e:
        log.error("Failed to mark task %s as completed: %s", task_id, e)


def mark_stale_tasks_failed(stale_minutes: int = 30) -> int:
    """
    Mark queued/running/retrying tasks as failed when they have not been updated
    for a long time, preventing permanent "pending/running" UI states.
    """
    try:
        from finder.shared.database import _USE_POSTGRES
        with transaction() as conn:
            if _USE_POSTGRES:
                exists = conn.execute("SELECT to_regclass('public.task_status') AS t").fetchone()
                exists_val = None
                if exists:
                    try:
                        exists_val = exists.get("t")
                    except Exception:
                        try:
                            exists_val = exists["t"]
                        except Exception:
                            exists_val = None
                if not exists_val:
                    return 0
            else:
                exists = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='task_status'"
                ).fetchone()
                if not exists:
                    return 0

            if _USE_POSTGRES:
                cur = conn.execute(
                    """
                    UPDATE task_status
                    SET status='failed',
                        failure_reason='stale task watchdog timeout',
                        completed_at=CURRENT_TIMESTAMP,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE status IN ('queued','running','retrying')
                      AND updated_at < (CURRENT_TIMESTAMP - (? || ' minutes')::interval)
                    """,
                    (str(int(stale_minutes)),),
                )
            else:
                cur = conn.execute(
                    """
                    UPDATE task_status
                    SET status='failed',
                        failure_reason='stale task watchdog timeout',
                        completed_at=CURRENT_TIMESTAMP,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE status IN ('queued','running','retrying')
                      AND updated_at < datetime('now', ?)
                    """,
                    (f"-{int(stale_minutes)} minutes",),
                )
            return int(getattr(cur, "rowcount", 0) or 0)
    except Exception as e:
        log.error("Failed stale task watchdog: %s", e)
        return 0
