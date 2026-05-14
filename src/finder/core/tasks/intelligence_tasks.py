"""
src/finder/core/tasks/intelligence_tasks.py
-------------------------------------------
Celery tasks for Phase C Intelligence features.
Handles async embedding generation and adaptive memory processing.
"""

from finder.shared.celery_app import celery_app
from finder.shared.logging import get_logger
from finder.api.sockets import emit_event
from finder.core.intelligence.semantic_matcher import compute_embedding

log = get_logger("intelligence_tasks")


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def task_compute_job_embedding(self, job_url: str, job_text: str):
    """
    Asynchronously compute and cache the semantic embedding for a job.
    Called during the matching pipeline.
    """
    try:
        log.info("Computing semantic embedding for job: %s", job_url)
        emit_event("matching:started", {"job_url": job_url, "phase": "semantic_embedding"})
        
        # This will compute and cache it in the DB
        compute_embedding(text=job_text, source_type="job", source_id=job_url, use_cache=True)
        
        emit_event("matching:completed", {"job_url": job_url, "phase": "semantic_embedding"})
        return {"status": "success", "job_url": job_url}
    except Exception as exc:
        log.error("Failed to compute embedding for %s: %s", job_url, exc, exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2)
def task_compute_resume_embedding(self, user_id: str, resume_text: str):
    """
    Compute and cache the embedding for the user's resume.
    """
    try:
        log.info("Computing semantic embedding for resume: %s", user_id)
        compute_embedding(text=resume_text, source_type="resume", source_id=str(user_id), use_cache=True)
        return {"status": "success"}
    except Exception as exc:
        log.error("Failed to compute resume embedding: %s", exc, exc_info=True)
        raise self.retry(exc=exc)

@celery_app.task(bind=True, max_retries=2)
def task_generate_reasoning(self, job_url: str, resume_skills: str, job_description: str, semantic_score: float):
    """Phase F: Generate explainable AI reasoning for a job match."""
    from finder.core.intelligence.reasoning_engine import generate_reasoning
    try:
        reasoning = generate_reasoning(job_url, resume_skills, job_description, semantic_score)
        emit_event("ai:reasoning_ready", {"job_url": job_url, "reasoning": reasoning})
        return {"status": "success", "job_url": job_url}
    except Exception as exc:
        log.error("Failed to generate AI reasoning: %s", exc)
        raise self.retry(exc=exc)

@celery_app.task(bind=True, max_retries=1)
def task_analyze_skill_gap(self, user_id: int):
    """Phase F: Generate a career strategy skill gap analysis."""
    from finder.core.intelligence.career_strategy_engine import generate_skill_gap_analysis
    try:
        insight = generate_skill_gap_analysis(user_id)
        emit_event("ai:strategy_insight", {"insight_type": "skill_gap", "insight": insight})
        
        # Send a smart notification
        from finder.shared.database import get_db
        with get_db() as conn:
            conn.execute(
                "INSERT INTO notifications (user_id, message, type) VALUES (?, 'New Career Strategy Insight generated based on recent applications.', 'ai_ready')",
                (user_id,)
            )
            
        emit_event("notifications:updated", {})
        return {"status": "success"}
    except Exception as exc:
        log.error("Failed to generate skill gap analysis: %s", exc)
        raise self.retry(exc=exc)
