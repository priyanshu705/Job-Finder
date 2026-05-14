"""
src/finder/core/tasks/ai_tasks.py
-----------------------------------
Celery tasks for AI content generation and follow-up drafting.
All tasks are synchronous – no async/await.
"""

from finder.shared.celery_app import celery_app
from finder.shared.logging import get_logger
from finder.api.sockets import emit_event

log = get_logger("ai_tasks")


@celery_app.task(bind=True, max_retries=2, default_retry_delay=5)
def task_generate_ai_content(self, generation_type: str, context: dict, job_id: int = None):
    """
    Generate AI content (cover letter, hire-me answer, etc.) for a job.
    Stores result in ai_generations and emits realtime events.
    """
    from finder.core.ai.ai_service import generate_content
    try:
        log.info("AI task started: %s (job_id=%s)", generation_type, job_id)
        result = generate_content(generation_type, context)
        log.info("AI task completed: %s", generation_type)
        return {"generation_type": generation_type, "result": result, "job_id": job_id}
    except Exception as exc:
        log.error("AI task failed (%s): %s", generation_type, exc, exc_info=True)
        emit_event("ai:generation_completed", {"type": generation_type, "success": False, "error": str(exc)})
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def task_generate_followup(self, job_url: str, followup_type: str = "recruiter",
                            company_name: str = "", job_title: str = ""):
    """
    Generate a follow-up email draft for a specific job application.
    Saves draft to followup_queue for user review/copy.
    """
    from finder.core.followup.service import generate_followup_draft
    try:
        log.info("Follow-up task: %s for %s", followup_type, job_url)
        result = generate_followup_draft(
            job_url=job_url,
            followup_type=followup_type,
            company_name=company_name,
            job_title=job_title,
        )
        log.info("Follow-up draft created: id=%s", result.get("id"))
        return result
    except Exception as exc:
        log.error("Follow-up task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
