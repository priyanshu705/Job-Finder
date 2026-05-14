"""
src/finder/core/followup/service.py
-------------------------------------
AI-powered follow-up draft generator.
Generates drafts ONLY – no auto-sending.
All drafts go into followup_queue for user approval/copy/send manually.
"""

import logging
from datetime import datetime
from finder.shared.database import get_db, _USE_POSTGRES
from finder.api.sockets import emit_event
from finder.core.ai.ai_service import generate_content

log = logging.getLogger("followup_service")

FOLLOWUP_TYPES = {
    "interview":  "Post-interview thank-you + reaffirmation of interest",
    "recruiter":  "Application status follow-up to recruiter",
    "rejection":  "Graceful rejection recovery + keeping door open",
    "networking": "LinkedIn connection request or networking message",
}


def generate_followup_draft(
    job_url: str,
    followup_type: str = "recruiter",
    company_name: str = "",
    job_title: str = "",
) -> dict:
    """Generate and persist a follow-up draft. Returns the saved row dict."""
    if followup_type not in FOLLOWUP_TYPES:
        followup_type = "recruiter"

    context = {
        "company_name":  company_name or "the company",
        "job_title":     job_title or "the position",
        "followup_type": followup_type,
    }

    emit_event("followup:generated", {"job_url": job_url, "type": followup_type})
    draft = generate_content("followup_email", context)

    row_id = _save_draft(job_url, followup_type, draft)

    emit_event("followup:queued", {
        "id":      row_id,
        "job_url": job_url,
        "type":    followup_type,
        "company": company_name,
    })
    log.info("Follow-up draft saved id=%s type=%s", row_id, followup_type)
    return {"id": row_id, "type": followup_type, "draft": draft, "status": "draft"}


def _save_draft(job_url: str, followup_type: str, draft: str) -> int:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        if _USE_POSTGRES:
            rows = conn.execute(
                "INSERT INTO followup_queue (job_url, type, draft_content, updated_at) "
                "VALUES (?,?,?,?) RETURNING id",
                (job_url, followup_type, draft, now)
            ).fetchall()
            return rows[0]["id"] if rows else None
        else:
            cur = conn.execute(
                "INSERT INTO followup_queue (job_url, type, draft_content, updated_at) "
                "VALUES (?,?,?,?)",
                (job_url, followup_type, draft, now)
            )
            return cur.lastrowid


def get_followup_queue(status: str = None, limit: int = 50) -> list:
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
    if status not in {"approved", "dismissed", "draft"}:
        return False
    with get_db() as conn:
        conn.execute(
            "UPDATE followup_queue SET status=?, updated_at=? WHERE id=?",
            (status, datetime.utcnow().isoformat(), followup_id)
        )
    return True
