"""
src/finder/core/tasks/agent_tasks.py
------------------------------------
Celery wrappers for long-running agent operations.
Replaces threading.Thread to provide retry-safety and persistence.
"""

from finder.shared.celery_app import celery_app
from finder.shared.task_tracker import create_task_record, update_task_status, mark_task_failed, mark_task_completed
from finder.shared.logging import get_logger
from finder.api.sockets import emit_event

log = get_logger("agent_tasks")

def _task_wrapper(self, task_type: str, func, *args, **kwargs):
    """
    Standardizes task lifecycle tracking in the task_status table.
    """
    task_id = self.request.id
    retry_count = self.request.retries
    
    # Only create the record on first run
    if retry_count == 0:
        create_task_record(task_id, task_type)
        
    update_task_status(task_id, 'running', retry_count)
    log.info("Starting task %s (%s)", task_type, task_id)
    emit_event('agent:status', {'task': task_type, 'status': 'started', 'task_id': task_id})
    
    try:
        result = func(*args, **kwargs)
        mark_task_completed(task_id)
        log.info("Completed task %s (%s)", task_type, task_id)
        emit_event('agent:status', {'task': task_type, 'status': 'completed', 'task_id': task_id})
        return result
    except Exception as exc:
        failure_reason = str(exc)
        log.error("Failed task %s (%s): %s", task_type, task_id, failure_reason, exc_info=True)
        # If we are going to retry, we keep it as retrying
        if self.request.retries < self.max_retries:
            update_task_status(task_id, 'retrying', retry_count + 1)
            emit_event('agent:status', {'task': task_type, 'status': 'retrying', 'task_id': task_id, 'reason': failure_reason})
            raise self.retry(exc=exc)
        else:
            mark_task_failed(task_id, failure_reason)
            emit_event('agent:status', {'task': task_type, 'status': 'failed', 'task_id': task_id, 'reason': failure_reason})
            
            # Route to Dead Letter Queue (DLQ)
            try:
                from finder.shared.database import get_db
                with get_db() as conn:
                    conn.execute(
                        "INSERT INTO task_failure_audit (task_id, task_type, error_type, trace_id) VALUES (?, ?, ?, ?)",
                        (task_id, task_type, type(exc).__name__, "trace_dlq")
                    )
            except Exception as dlq_exc:
                log.error("Failed to write to DLQ: %s", dlq_exc)
                
            raise exc

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10, time_limit=900, soft_time_limit=840)
def task_run_cycle(self, query: str = "", scraper_pages: int = 0, headless: bool = True):
    from finder.core.agent import run_agent_cycle
    from finder.shared.redis_cache import get_cache
    cache = get_cache()
    if not cache.acquire_lock("cycle", timeout_seconds=600):
        log.warning("Cycle already running, skipping duplicate task execution.")
        return {"status": "skipped", "reason": "lock_acquired"}
    try:
        return _task_wrapper(self, 'agent', lambda: run_agent_cycle(query=query, scraper_pages=scraper_pages, headless=headless))
    finally:
        cache.release_lock("cycle")

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10, time_limit=600, soft_time_limit=540)
def task_run_scraper(self, headless: bool = True):
    from finder.core.scraper.service import run_scraper
    from finder.shared.redis_cache import get_cache
    cache = get_cache()
    if not cache.acquire_lock("scraper", timeout_seconds=500):
        log.warning("Scraper already running, skipping duplicate task execution.")
        return {"status": "skipped", "reason": "lock_acquired"}
    try:
        return _task_wrapper(self, 'scraper', lambda: run_scraper(headless=headless))
    finally:
        cache.release_lock("scraper")

@celery_app.task(bind=True, max_retries=2, default_retry_delay=10, time_limit=600, soft_time_limit=540)
def task_run_discovery(self, headless: bool = True):
    from finder.core.scraper.discovery import run_discovery_scrapers
    return _task_wrapper(self, 'discovery', lambda: run_discovery_scrapers(headless=headless))

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10, time_limit=300, soft_time_limit=270)
def task_run_matcher(self):
    from finder.core.matcher import run_matcher
    return _task_wrapper(self, 'matcher', run_matcher)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10, time_limit=180, soft_time_limit=150)
def task_run_ranker(self):
    from finder.core.queue import run_queue
    return _task_wrapper(self, 'queue', run_queue)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10, time_limit=300, soft_time_limit=270)
def task_generate_assistant(self):
    from finder.core.apply_bot.answer_generator import generate_smart_answers
    return _task_wrapper(self, 'assistant', generate_smart_answers)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def task_sheets_sync(self):
    from finder.core.sheets import run_sheets_sync
    return _task_wrapper(self, 'sheets', run_sheets_sync)

@celery_app.task(bind=True, max_retries=1, default_retry_delay=10)
def task_parse_resume(self, file_path: str):
    from finder.shared.resume_parser import analyze_resume
    from finder.shared.database import transaction
    import json
    
    emit_event('parsing:started', {'file': file_path})
    try:
        skills, roles, queries = analyze_resume(file_path)
        emit_event('parsing:progress', {'status': 'extracting'})
        
        with transaction() as conn:
            conn.execute("""
                UPDATE resume_profile 
                SET skills = ?, detected_roles = ?, generated_queries = ?, 
                    parsing_status = 'completed', uploaded_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (json.dumps(skills), json.dumps(roles), json.dumps(queries)))
            
            conn.execute("""
                INSERT INTO resume_versions (user_id, skills, detected_roles)
                VALUES (1, ?, ?)
            """, (json.dumps(skills), json.dumps(roles)))
            
        # Trigger adaptive intelligence
        from finder.core.intelligence.adaptive_search import initialize_queries
        initialize_queries(queries)
        
        # Reset matching queue
        from finder.shared.queue_utils import reset_active_queue
        reset_active_queue()
        
        emit_event('parsing:complete', {'skills': skills, 'roles': roles, 'queries': queries})
        emit_event('queue:updated', {})
        
        # Start matching
        task_run_cycle.delay(headless=True)
        return True
    except Exception as e:
        emit_event('parsing:failed', {'error': str(e)})
        raise e
    finally:
        import os
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
