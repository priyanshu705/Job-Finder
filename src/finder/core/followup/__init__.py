"""
src/finder/core/followup/service.py
-------------------------------------
AI-powered follow-up draft generator.
Generates drafts ONLY – no auto-sending.
All drafts go into followup_queue for user approval/copy/send.
"""

import logging
from datetime import datetime
from finder.shared.database import get_db
from finder.api.sockets import emit_event
from finder.core.ai.ai_service import generate_content

log = logging.getLogger("followup_service")

FOLLOWUP_TYPES = {
    "interview":   "Post-interview thank-you + reaffirmation of interest",
    "recruiter":   "Application status follow-up to recruiter",
    "rejection":   "Graceful rejection recovery + keeping door open",
    "networking":  "LinkedIn connection request or networking message",
}


def generate_followup_draft(job_url: str, followup_type: str = "recruiter",
                             company_name: str = "", job_title: str = "") -> dict:
    """
    Generate a follow-up email draft using Gemini and save it to followup_queue.
    Returns the saved queue row as a dict.
    """
    if followup_type not in FOLLOWUP_TYPES:
        followup_type = "recruiter"

    context = {
        "company_name":  company_name or "the company",
        "job_title":     job_title or "the position",
        "followup_type": followup_type,
    }

    emit_event("followup:generated", {"job_url": job_url, "type": followup_type})
    draft = generate_content("followup_email", context)

    # Save to followup_queue
    row_id = _save_draft(job_url, followup_type, draft)

    emit_event("followup:queued", {
        "id": row_id,
        "job_url": job_url,
        "type": followup_type,
        "company": company_name,
    })
    log.info("Follow-up draft saved (id=%s, type=%s, job=%s)", row_id, followup_type, job_url)
    return {"id": row_id, "type": followup_type, "draft": draft, "status": "draft"}


def _save_draft(job_url: str, followup_type: str, draft: str) -> int:
    with get_db() as conn:
        if _is_postgres():
            rows = conn.execute(
                "INSERT INTO followup_queue (job_url, type, draft_content, updated_at) "
                "VALUES (?,?,?,?) RETURNING id",
                (job_url, followup_type, draft, datetime.utcnow().isoformat())
            ).fetchall()
            return rows[0]["id"] if rows else None
        else:
            cur = conn.execute(
                "INSERT INTO followup_queue (job_url, type, draft_content, updated_at) "
                "VALUES (?,?,?,?)",
                (job_url, followup_type, draft, datetime.utcnow().isoformat())
            )
            return cur.lastrowid


def _is_postgres() -> bool:
    from finder.shared.database import _USE_POSTGRES
    return _USE_POSTGRES


def get_followup_queue(status: str = None, limit: int = 50) -> list:
    """Return follow-up queue rows, optionally filtered by status."""
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT f.*, j.title as job_title_ref, j.company "
                "FROM followup_queue f LEFT JOIN jobs j ON f.job_url = j.job_url "
                "WHERE f.status = ? ORDER BY f.created_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT f.*, j.title as job_title_ref, j.company "
                "FROM followup_queue f LEFT JOIN jobs j ON f.job_url = j.job_url "
                "ORDER BY f.created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows] if rows else []


def update_followup_status(followup_id: int, status: str) -> bool:
    """Approve or dismiss a follow-up draft."""
    allowed = {"approved", "dismissed", "draft"}
    if status not in allowed:
        return False
    with get_db() as conn:
        conn.execute(
            "UPDATE followup_queue SET status=?, updated_at=? WHERE id=?",
            (status, datetime.utcnow().isoformat(), followup_id)
        )
    return True
