"""
src/finder/core/tasks/interview_tasks.py
----------------------------------------
Phase E: Interview Preparation Mode
Uses Gemini to generate mock interviews based on the resume and a specific job match.
"""

import os
import json
import logging
from finder.shared.celery_app import celery_app
from finder.shared.database import get_db
from finder.api.sockets import emit_event

log = logging.getLogger("interview_prep")

@celery_app.task(bind=True, max_retries=2, retry_backoff=True)
def task_generate_interview_prep(self, job_url: str):
    """
    Generate interview preparation questions using Gemini Free Tier.
    """
    log.info(f"Generating interview prep for job: {job_url}")
    emit_event("ai:prep_started", {"job_url": job_url})
    
    try:
        from google.generativeai import configure, GenerativeModel
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY missing")
            
        configure(api_key=api_key)
        model = GenerativeModel('gemini-1.5-flash')
        
        # 1. Fetch Job and Resume Context
        with get_db() as conn:
            job_row = conn.execute("SELECT title, company, description FROM jobs WHERE job_url = ?", (job_url,)).fetchone()
            resume_row = conn.execute("SELECT skills, detected_roles FROM resume_versions ORDER BY created_at DESC LIMIT 1").fetchone()
            
            if not resume_row:
                # Fallback to older resume_profile table
                resume_row = conn.execute("SELECT skills, detected_roles FROM resume_profile LIMIT 1").fetchone()
                
        if not job_row or not resume_row:
            raise ValueError("Missing job or resume context for interview generation")
            
        # 2. Prompt Gemini
        prompt = f"""
        You are an expert technical recruiter and hiring manager.
        The candidate has the following skills: {resume_row['skills']}
        They are applying for: {job_row['title']} at {job_row['company']}
        
        Job Description:
        {job_row['description'][:1500]}
        
        Provide an interview preparation guide structured EXACTLY like this JSON:
        {{
            "technical_questions": ["Question 1", "Question 2", "Question 3"],
            "behavioral_questions": ["Question 1", "Question 2", "Question 3"],
            "hr_questions": ["Question 1"],
            "role_play_scenario": "A brief scenario they might be asked to solve on the spot"
        }}
        
        ONLY return valid JSON. Do not include markdown blocks.
        """
        
        response = model.generate_content(prompt)
        text_resp = response.text.replace("```json", "").replace("```", "").strip()
        prep_data = json.loads(text_resp)
        
        # 3. Persist Generation
        with get_db() as conn:
            # We can store this in user_controls or add a column to jobs/apply_queue
            key = f"prep_{job_url}"
            conn.execute(
                "DELETE FROM user_controls WHERE key = ?", (key,)
            )
            conn.execute(
                "INSERT INTO user_controls (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (key, json.dumps(prep_data))
            )
            
            # Create smart notification
            conn.execute(
                "INSERT INTO notifications (message, type) VALUES (?, 'ai_ready')",
                (f"Interview prep is ready for {job_row['title']} at {job_row['company']}!",)
            )
            
        emit_event("ai:prep_completed", {"job_url": job_url, "data": prep_data})
        emit_event("notifications:updated", {})
        return True
        
    except Exception as exc:
        log.error("Failed to generate interview prep: %s", exc)
        emit_event("ai:prep_failed", {"job_url": job_url, "error": str(exc)})
        raise self.retry(exc=exc)
