"""
src/finder/api/resume.py
------------------------
Resume Management Blueprint.
Handles upload, parsing orchestration, and queue reset triggers.
"""

import os
import json
import uuid
from flask import Blueprint, request, current_app
from finder.shared.database import get_db, fetch_one_dict, transaction
from finder.shared.config import get_resume_upload_dir, ENABLE_RESUME_UPLOADS
from finder.shared.response import success_response, error_response
from finder.shared.errors import ResumeError, InvalidFileError, ParsingError, FileTooLargeError
from finder.shared.validation import validate_resume_upload
from finder.shared.logging import get_logger, timed
from finder.api.sockets import emit_event

log = get_logger("api.resume")
bp = Blueprint("resume", __name__, url_prefix="/api/resume")

@bp.route("", methods=["GET"])
@timed
def get_resume():
    """Fetch the active resume profile."""
    try:
        with get_db() as conn:
            row = fetch_one_dict(conn, "SELECT * FROM resume_profile WHERE id = 1")
            
        if row:
            return success_response(
                message="Resume profile found",
                data={
                    "filename": row.get("filename"),
                    "skills": json.loads(row.get("skills") or "{}"),
                    "roles": json.loads(row.get("detected_roles") or "[]"),
                    "queries": json.loads(row.get("generated_queries") or "[]"),
                    "parsing_status": row.get("parsing_status"),
                    "uploaded_at": row.get("uploaded_at"),
                    "source": "db"
                }
            )
        return success_response("No resume found", data=None)
    except Exception as e:
        log.error("Failed to fetch resume: %s", e)
        return error_response("FETCH_FAILED", "Failed to retrieve resume profile", 500)

@bp.route("", methods=["POST"])
@timed
def upload_resume():
    """Handle resume upload, validation, parsing, and pipeline trigger."""
    if not ENABLE_RESUME_UPLOADS:
        return error_response("UPLOADS_DISABLED", "Resume uploads are currently disabled", 403)
        
    save_path = None
    try:
        # 1. Validation
        file_obj = request.files.get("file")
        safe_name, ext, size = validate_resume_upload(file_obj)
        
        # 2. Save Temporary
        upload_dir = get_resume_upload_dir()
        temp_filename = f"{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(upload_dir, temp_filename)
        file_obj.save(save_path)
        log.info("Resume saved temporarily", extra={"path": save_path, "size": size})
        
        # 3. UPSERT into DB with 'parsing' status
        with transaction() as conn:
            conn.execute("""
                INSERT INTO resume_profile (id, filename, parsing_status, uploaded_at)
                VALUES (1, ?, 'parsing', CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET 
                    filename = excluded.filename,
                    parsing_status = 'parsing',
                    uploaded_at = CURRENT_TIMESTAMP
            """, (safe_name,))
            
        log.info("Queueing parsing task for %s", temp_filename)
        
        # 4. Trigger Background Task
        from finder.core.tasks.agent_tasks import task_parse_resume
        task_parse_resume.delay(save_path)
        
        return success_response(
            "Resume uploaded. AI analysis started in the background.",
            data={
                "filename": safe_name,
                "status": "parsing"
            }
        )
        
    except ResumeError as re:
        error_msg = getattr(re, "detail", str(re))
        log.error("Resume business error: %s", error_msg)
        _mark_failed()
        _cleanup_temp(save_path)
        return error_response(re.__class__.__name__.upper(), error_msg, 400)
    except Exception as e:
        log.error("Unexpected upload error: %s", e, exc_info=True)
        _mark_failed()
        _cleanup_temp(save_path)
        return error_response("INTERNAL_ERROR", "An unexpected error occurred during upload", 500)

def _cleanup_temp(save_path):
    if save_path and os.path.exists(save_path):
        try:
            os.remove(save_path)
        except Exception as e:
            log.warning("Failed to remove temp resume file: %s", e)

def _mark_failed():
    try:
        with transaction() as conn:
            conn.execute("UPDATE resume_profile SET parsing_status = 'failed', updated_at = CURRENT_TIMESTAMP WHERE id = 1")
    except Exception as e:
        log.error("Failed to mark resume as failed: %s", e)
