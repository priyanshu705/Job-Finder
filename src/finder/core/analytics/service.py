"""
src/finder/core/analytics/service.py
--------------------------------------
Analytics computation service for the AutoApply AI platform.
"""

import logging
from datetime import date, timedelta
from finder.shared.database import get_db

log = logging.getLogger("analytics_service")


def _q(conn, sql, params=()):
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows] if rows else []

def _q1(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else {}


def get_overview_metrics() -> dict:
    with get_db() as conn:
        totals = _q1(conn, """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status IN ('applied','applied_manual') THEN 1 ELSE 0 END) as applied,
                SUM(CASE WHEN status = 'interview' THEN 1 ELSE 0 END)                   as interviews,
                SUM(CASE WHEN status = 'rejected'  THEN 1 ELSE 0 END)                   as rejected,
                SUM(CASE WHEN status = 'pending'   THEN 1 ELSE 0 END)                   as pending,
                AVG(match_score_at_apply) as avg_score
            FROM apply_queue
        """)
        applied    = totals.get("applied") or 0
        interviews = totals.get("interviews") or 0
        rejected   = totals.get("rejected") or 0
        total      = totals.get("total") or 1
        return {
            "total_applications": applied,
            "approval_rate":      round(applied / total * 100, 1),
            "rejection_rate":     round(rejected / total * 100, 1),
            "interview_rate":     round(interviews / max(applied, 1) * 100, 1),
            "pending":            totals.get("pending") or 0,
            "avg_match_score":    round(totals.get("avg_score") or 0, 1),
        }


def get_top_skills(limit: int = 10) -> list:
    with get_db() as conn:
        return _q(conn,
            "SELECT skill, SUM(count) as total FROM skill_outcome_map "
            "GROUP BY skill ORDER BY total DESC LIMIT ?", (limit,))


def get_top_roles(limit: int = 8) -> list:
    with get_db() as conn:
        return _q(conn, """
            SELECT j.title, COUNT(*) as count
            FROM apply_queue q LEFT JOIN jobs j ON q.job_url = j.job_url
            WHERE j.title IS NOT NULL
            GROUP BY j.title ORDER BY count DESC LIMIT ?
        """, (limit,))


def get_platform_stats() -> list:
    with get_db() as conn:
        rows = _q(conn, """
            SELECT j.platform,
                   COUNT(*) as total,
                   SUM(CASE WHEN q.status IN ('applied','applied_manual') THEN 1 ELSE 0 END) as applied,
                   SUM(CASE WHEN q.status = 'interview' THEN 1 ELSE 0 END) as interviews
            FROM apply_queue q
            LEFT JOIN jobs j ON q.job_url = j.job_url
            WHERE j.platform IS NOT NULL
            GROUP BY j.platform ORDER BY applied DESC
        """)
        for r in rows:
            r["success_rate"] = round(r["applied"] / max(r["total"], 1) * 100, 1)
        return rows


def get_response_trend(days: int = 30) -> list:
    since = (date.today() - timedelta(days=days)).isoformat()
    with get_db() as conn:
        return _q(conn, """
            SELECT CAST(updated_at AS DATE) as day,
                   COUNT(*) as total,
                   SUM(CASE WHEN status IN ('applied','applied_manual') THEN 1 ELSE 0 END) as applied,
                   SUM(CASE WHEN status = 'interview' THEN 1 ELSE 0 END) as interviews,
                   SUM(CASE WHEN status = 'rejected'  THEN 1 ELSE 0 END) as rejected
            FROM apply_queue
            WHERE updated_at >= ? AND updated_at IS NOT NULL
            GROUP BY CAST(updated_at AS DATE)
            ORDER BY CAST(updated_at AS DATE) ASC
        """, (since,))


def get_ai_usage_stats() -> dict:
    with get_db() as conn:
        totals = _q1(conn, """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN provider='gemini'   THEN 1 ELSE 0 END) as gemini,
                   SUM(CASE WHEN provider='fallback' THEN 1 ELSE 0 END) as fallback
            FROM ai_generations
        """)
        today = (_q1(conn,
            "SELECT COUNT(*) as cnt FROM ai_generations WHERE date(created_at)=date('now')"
        ).get("cnt") or 0)
        by_type = _q(conn,
            "SELECT generation_type, COUNT(*) as cnt FROM ai_generations "
            "GROUP BY generation_type ORDER BY cnt DESC")
        return {
            "total_generations": totals.get("total") or 0,
            "gemini_calls":      totals.get("gemini") or 0,
            "fallback_calls":    totals.get("fallback") or 0,
            "today_calls":       today,
            "by_type":           by_type,
        }


def save_snapshot(metric_name: str, metric_value: float, dimension: str = None):
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO analytics_snapshots (metric_name, metric_value, dimension) VALUES (?,?,?)",
                (metric_name, metric_value, dimension)
            )
    except Exception as exc:
        log.warning("Snapshot save failed: %s", exc)


def take_daily_snapshot():
    metrics = get_overview_metrics()
    for key, val in metrics.items():
        if isinstance(val, (int, float)):
            save_snapshot(key, float(val))
    log.info("Daily analytics snapshot saved.")


def compute_kpis() -> dict:
    return {
        "overview": get_overview_metrics(),
        "ai_usage": get_ai_usage_stats(),
        "platforms": get_platform_stats(),
        "trends": get_response_trend(),
        "top_roles": get_top_roles()
    }
