"""
src/finder/core/apply_bot/engine.py
----------------------------------
Hardened Application Assistant — Finder V6.
Rate limits, safety delays, and state consistency.
"""

import os
import json
import time
import sys
import random
from playwright.sync_api import sync_playwright, Page
from finder.shared.logger import get_logger
from finder.shared.database import get_db
from finder.core.apply_bot.answer_generator import generate_smart_answers

log = get_logger("apply_assistant")

# Constants
MAX_JOBS_PER_RUN = 5
ACTION_DELAY_SEC = (2, 5)

def _update_job_status(job_id, status, error=None):
    with get_db() as conn:
        conn.execute(
            "UPDATE apply_queue SET status=?, last_error=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, error, job_id)
        )

def detect_verification(page: Page):
    content = page.content().lower()
    for p in ["verify you are human", "captcha", "robot", "blocked"]:
        if p in content: return p
    return None

def run_apply_assistant(headless: bool = False, page=None) -> dict:
    log.info("🚀 Starting Hardened Apply Assistant Cycle...")
    
    with get_db() as conn:
        threshold = float(conn.execute("SELECT value FROM user_controls WHERE key='min_match'").fetchone()[0])
        jobs = [dict(r) for r in conn.execute(
            "SELECT q.id, q.job_url, q.assistant_data, j.title, j.company, j.skills FROM apply_queue q "
            "JOIN jobs j ON j.job_url = q.job_url "
            "WHERE q.status IN ('pending', 'ready_to_apply', 'opened') AND q.match_score_at_apply >= ? "
            "ORDER BY q.match_score_at_apply DESC LIMIT ?", 
            (threshold, MAX_JOBS_PER_RUN)
        ).fetchall()]

    if not jobs:
        log.info("No eligible jobs found in queue.")
        return {"count": 0}

    stats = {"processed": 0, "applied": 0, "safety_stops": 0}

    def _process(p: Page):
        for job in jobs:
            log.info(f"👉 Processing: {job['title']} @ {job['company']}")
            
            # Safety Delay
            delay = random.uniform(*ACTION_DELAY_SEC) if 'random' in globals() else 3
            time.sleep(delay)

            try:
                p.goto(job['job_url'], wait_until="networkidle")
                
                # Check for verification
                challenge = detect_verification(p)
                if challenge:
                    log.warning(f"🛑 SAFETY STOP: Verification detected ({challenge})")
                    _update_job_status(job['id'], 'verification_required', challenge)
                    stats['safety_stops'] += 1
                    break # Stop entire cycle for safety

                # State Consistency: Mark as 'opened' for human review
                _update_job_status(job['id'], 'opened')
                
                # Pre-generate answers if missing
                if not job.get('assistant_data'):
                    ai_data = generate_smart_answers(job)
                    with get_db() as conn:
                        conn.execute("UPDATE apply_queue SET assistant_data=? WHERE id=?", (json.dumps(ai_data), job['id']))

                # Wait for user via DB polling (consistent with UI actions)
                # In production, we'd wait for a 'confirm_applied' status
                stats['processed'] += 1
                log.info(f"Waiting for human action on {job['company']}...")
                
                # For this hardened version, we'll wait up to 5 mins per job
                wait_start = time.time()
                while time.time() - wait_start < 300:
                    with get_db() as conn:
                        row = conn.execute("SELECT status FROM apply_queue WHERE id=?", (job['id'],)).fetchone()
                        if row['status'] in ['applied_manual', 'skipped']:
                            if row['status'] == 'applied_manual': stats['applied'] += 1
                            break
                    time.sleep(2)
                
            except Exception as e:
                log.error(f"Error processing {job['company']}: {e}")
                _update_job_status(job['id'], 'failed', str(e))

    if page: _process(page)
    else:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            ctx = browser.new_context()
            p = ctx.new_page()
            _process(p)
            browser.close()

    return stats

from finder.core.intelligence.profile import get_profile_summary

def generate_smart_answers(job: dict) -> dict:
    """Generate intelligent, tailored answers for common application questions."""
    profile = get_profile_summary()
    skills = profile["skills"]
    jd = (job.get("description", "") + " " + job.get("skills", "")).lower()
    
    # Extract specific matches for the cover letter
    matching_skills = [s for s in skills if s in jd]
    
    # Template-based intelligent generation (avoids hallucination)
    hire_me = f"I am a highly motivated developer with expertise in {', '.join(skills[:3])}. "
    if matching_skills:
        hire_me += f"I have direct experience with {', '.join(matching_skills[:2])} which aligns perfectly with your requirements."
    else:
        hire_me += "I am eager to apply my technical skills to contribute to your team's goals."
        
    availability = "I am available to start immediately and can commit to a full-time role."
    
    return {
        "why_hire_me": hire_me,
        "availability": availability,
        "experience": f"I have been working with technologies like {', '.join(skills[:4])} and I'm always learning new stacks.",
        "skills_matched": matching_skills
    }
