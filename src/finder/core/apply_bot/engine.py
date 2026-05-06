"""
src/finder/core/apply_bot/engine.py
----------------------------------
Hardened Application Assistant — AutoApply AI.
Opens job pages for human review without blocking the agent cycle.
"""

import os
import json
import time
import random
from playwright.sync_api import sync_playwright, Page
from finder.shared.logger import get_logger
from finder.shared.database import get_db
from finder.core.apply_bot.answer_generator import generate_smart_answers  # single source of truth

log = get_logger("apply_assistant")

# Constants
MAX_JOBS_PER_RUN = 5
ACTION_DELAY_SEC = (1, 3)


def _update_job_status(job_id: int, status: str, error: str = None) -> None:
    """Atomically update a job's status in the queue."""
    with get_db() as conn:
        conn.execute(
            "UPDATE apply_queue SET status=?, last_error=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, error, job_id)
        )


def _ensure_assistant_data(job: dict) -> dict:
    """
    Return existing assistant_data (parsed) if valid, otherwise generate
    fresh data, persist it to DB, and return it.
    """
    raw = job.get("assistant_data")
    if raw:
        try:
            existing = json.loads(raw) if isinstance(raw, str) else raw
            # Validate it has the key fields the UI needs
            if existing.get("cover_letter") or existing.get("explanation"):
                return existing
        except Exception:
            pass  # corrupt JSON — fall through to regenerate

    log.info(f"Generating assistant data for: {job.get('title','?')} @ {job.get('company','?')}")
    ai_data = generate_smart_answers(job)
    with get_db() as conn:
        conn.execute(
            "UPDATE apply_queue SET assistant_data=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (json.dumps(ai_data), job["id"])
        )
    return ai_data


def detect_verification(page: Page) -> str | None:
    """Check if a verification/CAPTCHA wall is present."""
    try:
        content = page.content().lower()
        for pattern in ["verify you are human", "captcha", "robot check", "blocked"]:
            if pattern in content:
                return pattern
    except Exception:
        pass
    return None


def run_apply_assistant(headless: bool = False, page: Page = None) -> dict:
    """
    Opens each 'ready_to_apply' job in the browser for human review.
    Marks jobs as 'opened' and ensures assistant_data is generated.
    Does NOT block waiting for human confirmation — that is handled
    asynchronously via the UI status update endpoints.
    """
    log.info("🚀 Starting Apply Assistant Cycle...")

    # Fetch eligible jobs
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM user_controls WHERE key='min_match'"
        ).fetchone()
        threshold = float(row["value"]) if row else 70.0

        jobs = [dict(r) for r in conn.execute(
            """
            SELECT q.id, q.job_url, q.assistant_data, q.match_score_at_apply,
                   j.title, j.company, j.skills, j.description
            FROM apply_queue q
            JOIN jobs j ON j.job_url = q.job_url
            WHERE q.status = 'ready_to_apply'
              AND (q.match_score_at_apply IS NULL OR q.match_score_at_apply >= ?)
            ORDER BY q.match_score_at_apply DESC
            LIMIT ?
            """,
            (threshold, MAX_JOBS_PER_RUN)
        ).fetchall()]

    if not jobs:
        log.info("No eligible ready_to_apply jobs found.")
        return {"opened": 0, "assistant_generated": 0, "safety_stops": 0, "errors": 0}

    stats = {"opened": 0, "assistant_generated": 0, "safety_stops": 0, "errors": 0}

    def _process(p: Page) -> None:
        for job in jobs:
            log.info(f"👉 Opening: {job['title']} @ {job['company']}")

            # Safety delay between jobs
            delay = random.uniform(*ACTION_DELAY_SEC)
            time.sleep(delay)

            try:
                p.goto(job["job_url"], wait_until="domcontentloaded", timeout=30_000)

                # CAPTCHA / verification guard
                challenge = detect_verification(p)
                if challenge:
                    log.warning(f"🛑 Verification detected ({challenge}). Stopping cycle.")
                    _update_job_status(job["id"], "verification_required", challenge)

                    # Signal to API layer that manual action is needed
                    with get_db() as conn:
                        conn.execute(
                            "INSERT OR REPLACE INTO user_controls (key, value) VALUES (?, ?)",
                            ("manual_verification_required", challenge)
                        )
                    stats["safety_stops"] += 1
                    break  # Stop entire cycle for safety

                # Pre-generate / ensure assistant_data BEFORE marking opened
                _ensure_assistant_data(job)
                stats["assistant_generated"] += 1

                # Mark job as opened — human can now act via the UI panel
                _update_job_status(job["id"], "opened")
                stats["opened"] += 1
                log.info(f"  ✅ Opened and ready: {job['company']}")

                # Brief pause to let page settle
                time.sleep(1.5)

            except Exception as e:
                log.error(f"Error processing {job.get('company','?')}: {e}")
                _update_job_status(job["id"], "failed", str(e))
                stats["errors"] += 1

    if page:
        _process(page)
    else:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = browser.new_context(viewport={"width": 1280, "height": 800})
            p = ctx.new_page()
            try:
                _process(p)
            finally:
                browser.close()

    log.info(
        f"Apply Assistant done: opened={stats['opened']} "
        f"assistant_generated={stats['assistant_generated']} "
        f"safety_stops={stats['safety_stops']} errors={stats['errors']}"
    )
    return stats
