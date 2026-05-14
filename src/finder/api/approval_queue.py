"""
src/finder/api/approval_queue.py
--------------------------------
PHASE A: Approval Queue (Human-in-the-Loop AI Review System)

Backend endpoints for approval-based application workflow.
"""

import json
import logging
from flask import Blueprint, request, jsonify, g
from finder.shared.database import get_db
from finder.shared.jwt_security import require_jwt, require_csrf

log = logging.getLogger(__name__)

queue_bp = Blueprint("approval_queue", __name__, url_prefix="/api/approval-queue")


@queue_bp.route("", methods=["GET"])
@require_jwt
def get_queue():
    """
    Get user's approval queue (pending items only).

    Query params:
        limit (int): Max items to return (default: 50)
        status (str): Filter by status - pending|approved|rejected|skipped

    Returns:
        200: List of queue items
    """
    db = get_db()
    limit = request.args.get("limit", 50, type=int)
    status = request.args.get("status", "pending", type=str)

    items = db.execute(
        """SELECT * FROM approval_queue_items 
           WHERE user_id = ? AND status = ?
           ORDER BY match_score DESC
           LIMIT ?""",
        (int(g.user_id), status, limit),
    ).fetchall()

    return jsonify([dict(row) for row in items]), 200


@queue_bp.route("/<int:item_id>", methods=["GET"])
@require_jwt
def get_item(item_id):
    """
    Get specific queue item details.

    Returns:
        200: Queue item
        404: Item not found
    """
    db = get_db()

    item = db.execute(
        """SELECT * FROM approval_queue_items 
           WHERE id = ? AND user_id = ?""",
        (item_id, int(g.user_id)),
    ).fetchone()

    if not item:
        return jsonify({"error": "Item not found"}), 404

    return jsonify(dict(item)), 200


@queue_bp.route("/<int:item_id>/approve", methods=["POST"])
@require_jwt
@require_csrf
def approve_item(item_id):
    """
    Approve application and mark ready to submit.

    Request JSON:
        ai_answers (dict, optional): Updated AI-generated answers

    Returns:
        200: Item approved
        404: Item not found
    """
    db = get_db()

    # Verify ownership
    item = db.execute(
        "SELECT * FROM approval_queue_items WHERE id = ? AND user_id = ?",
        (item_id, int(g.user_id)),
    ).fetchone()

    if not item:
        return jsonify({"error": "Item not found"}), 404

    # Update answers if provided
    data = request.json or {}
    if "ai_answers" in data:
        updated_answers = dict(json.loads(item["ai_answers_json"] or "{}"))
        updated_answers.update(data["ai_answers"])
        ai_answers_json = json.dumps(updated_answers)
    else:
        ai_answers_json = item["ai_answers_json"]

    # Update status
    db.execute(
        """UPDATE approval_queue_items 
           SET status = 'approved', 
               approved_at = CURRENT_TIMESTAMP,
               ai_answers_json = ?
           WHERE id = ?""",
        (ai_answers_json, item_id),
    )
    db.commit()

    log.info(f"Approved item {item_id} for user {g.user_id}")
    return jsonify({"status": "approved", "item_id": item_id}), 200


@queue_bp.route("/<int:item_id>/reject", methods=["POST"])
@require_jwt
@require_csrf
def reject_item(item_id):
    """
    Reject application (no further action).

    Request JSON:
        reason (str, optional): Why rejected

    Returns:
        200: Item rejected
        404: Item not found
    """
    db = get_db()

    item = db.execute(
        "SELECT * FROM approval_queue_items WHERE id = ? AND user_id = ?",
        (item_id, int(g.user_id)),
    ).fetchone()

    if not item:
        return jsonify({"error": "Item not found"}), 404

    data = request.json or {}
    reason = data.get("reason", "user-rejected")

    db.execute(
        """UPDATE approval_queue_items 
           SET status = 'rejected'
           WHERE id = ?""",
        (item_id,),
    )
    db.commit()

    log.info(f"Rejected item {item_id} for user {g.user_id}: {reason}")
    return jsonify({"status": "rejected", "item_id": item_id}), 200


@queue_bp.route("/<int:item_id>/skip", methods=["POST"])
@require_jwt
@require_csrf
def skip_item(item_id):
    """
    Skip item (remove from current queue, no decision).

    Returns:
        200: Item skipped
        404: Item not found
    """
    db = get_db()

    item = db.execute(
        "SELECT * FROM approval_queue_items WHERE id = ? AND user_id = ?",
        (item_id, int(g.user_id)),
    ).fetchone()

    if not item:
        return jsonify({"error": "Item not found"}), 404

    db.execute(
        """UPDATE approval_queue_items 
           SET status = 'skipped'
           WHERE id = ?""",
        (item_id,),
    )
    db.commit()

    log.info(f"Skipped item {item_id} for user {g.user_id}")
    return jsonify({"status": "skipped", "item_id": item_id}), 200


@queue_bp.route("/<int:item_id>", methods=["PUT"])
@require_jwt
@require_csrf
def update_item_answers(item_id):
    """
    Update AI-generated answers before approval.

    Request JSON:
        answers (dict): Updated answers by question key

    Returns:
        200: Updated
        404: Item not found
    """
    data = request.json or {}
    db = get_db()

    item = db.execute(
        "SELECT * FROM approval_queue_items WHERE id = ? AND user_id = ?",
        (item_id, int(g.user_id)),
    ).fetchone()

    if not item:
        return jsonify({"error": "Item not found"}), 404

    # Merge with existing answers
    answers = dict(json.loads(item["ai_answers_json"] or "{}"))
    answers.update(data.get("answers", {}))

    db.execute(
        """UPDATE approval_queue_items 
           SET ai_answers_json = ?
           WHERE id = ?""",
        (json.dumps(answers), item_id),
    )
    db.commit()

    log.info(f"Updated answers for item {item_id}")
    return jsonify({"status": "updated", "item_id": item_id}), 200


@queue_bp.route("/blacklist", methods=["POST"])
@require_jwt
@require_csrf
def add_blacklist():
    """
    Add company to user's blacklist.

    Request JSON:
        company (str): Company name to blacklist
        reason (str, optional): Reason for blacklisting

    Returns:
        201: Company blacklisted
        400: Missing company name
    """
    data = request.json or {}
    company = data.get("company", "").strip()
    reason = data.get("reason", "User preference")

    if not company:
        return jsonify({"error": "Company name required"}), 400

    db = get_db()
    db.execute(
        """INSERT INTO user_blacklist (user_id, company, reason) 
           VALUES (?, ?, ?)""",
        (int(g.user_id), company, reason),
    )
    db.commit()

    log.info(f"Blacklisted {company} for user {g.user_id}")
    return jsonify({"status": "blacklisted", "company": company}), 201


@queue_bp.route("/blacklist", methods=["GET"])
@require_jwt
def get_blacklist():
    """
    Get user's company blacklist.

    Returns:
        200: List of blacklisted companies
    """
    db = get_db()

    blacklist = db.execute(
        """SELECT id, company, reason, created_at FROM user_blacklist 
           WHERE user_id = ?
           ORDER BY created_at DESC""",
        (int(g.user_id),),
    ).fetchall()

    return jsonify([dict(row) for row in blacklist]), 200


@queue_bp.route("/blacklist/<int:blacklist_id>", methods=["DELETE"])
@require_jwt
@require_csrf
def remove_blacklist(blacklist_id):
    """
    Remove company from blacklist.

    Returns:
        200: Removed
        404: Not found
    """
    db = get_db()

    entry = db.execute(
        "SELECT id FROM user_blacklist WHERE id = ? AND user_id = ?",
        (blacklist_id, int(g.user_id)),
    ).fetchone()

    if not entry:
        return jsonify({"error": "Blacklist entry not found"}), 404

    db.execute("DELETE FROM user_blacklist WHERE id = ?", (blacklist_id,))
    db.commit()

    log.info(f"Removed blacklist entry {blacklist_id} for user {g.user_id}")
    return jsonify({"status": "removed"}), 200


@queue_bp.route("/stats", methods=["GET"])
@require_jwt
def get_stats():
    """
    Get queue statistics for user.

    Returns:
        200: Queue statistics
    """
    db = get_db()

    user_id = int(g.user_id)

    # Count by status
    stats = db.execute(
        """SELECT 
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
            COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved,
            COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected,
            COUNT(CASE WHEN status = 'applied' THEN 1 END) as applied,
            COUNT(CASE WHEN status = 'skipped' THEN 1 END) as skipped
           FROM approval_queue_items
           WHERE user_id = ?""",
        (user_id,),
    ).fetchone()

    return (
        jsonify(
            {
                "pending": stats["pending"],
                "approved": stats["approved"],
                "rejected": stats["rejected"],
                "applied": stats["applied"],
                "skipped": stats["skipped"],
            }
        ),
        200,
    )
