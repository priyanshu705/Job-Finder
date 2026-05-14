"""
src/finder/core/analytics/service.py
--------------------------------------
Analytics computation service for the AutoApply AI platform.
Reads from the existing DB tables and returns structured metrics.
Also saves periodic snapshots to analytics_snapshots for trends.
"""

import logging
from datetime import date, timedelta
from finder.shared.database import get_db

log = logging.getLogger("analytics_service")


def get_overview_metrics() -> dict:
    """Returns high-level KPI metrics."""
    with get_db() as conn:
        def q1(sql, params=()):
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else {}

        totals = q1("""
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
            "approval_rate":      round(applied / total * 100, 1) if total else 0,
            "rejection_rate":     round(rejected / total * 100, 1) if total else 0,
            "interview_rate":     round(interviews / max(applied, 1) * 100, 1),
            "pending":            totals.get("pending") or 0,
            "avg_match_score":    round(totals.get("avg_score") or 0, 1),
        }


def get_top_skills(limit: int = 10) -> list:
    """Return the top matched skills from scraped jobs."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT skill, SUM(count) as total FROM skill_outcome_map GROUP BY skill ORDER BY total DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows] if rows else []


def get_top_roles(limit: int = 8) -> list:
    """Return most frequent job titles in the queue."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT j.title, COUNT(*) as count
               FROM apply_queue q LEFT JOIN jobs j ON q.job_url = j.job_url
               WHERE j.title IS NOT NULL
               GROUP BY j.title ORDER BY count DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows] if rows else []


def get_platform_stats() -> list:
    """Success rate per platform."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT j.platform,
                   COUNT(*) as total,
                   SUM(CASE WHEN q.status IN ('applied','applied_manual') THEN 1 ELSE 0 END) as applied,
                   SUM(CASE WHEN q.status = 'interview' THEN 1 ELSE 0 END) as interviews
            FROM apply_queue q
            LEFT JOIN jobs j ON q.job_url = j.job_url
            WHERE j.platform IS NOT NULL
            GROUP BY j.platform
            ORDER BY applied DESC
        """).fetchall()
        result = []
        for r in (rows or []):
            d = dict(r)
            d["success_rate"] = round(d["applied"] / max(d["total"], 1) * 100, 1)
            result.append(d)
        return result


def get_response_trend(days: int = 30) -> list:
    """Daily application trend for the last N days."""
    since = (date.today() - timedelta(days=days)).isoformat()
    with get_db() as conn:
        rows = conn.execute("""
            SELECT CAST(updated_at AS DATE) as day,
                   COUNT(*) as total,
                   SUM(CASE WHEN status IN ('applied','applied_manual') THEN 1 ELSE 0 END) as applied,
                   SUM(CASE WHEN status = 'interview' THEN 1 ELSE 0 END) as interviews,
                   SUM(CASE WHEN status = 'rejected'  THEN 1 ELSE 0 END) as rejected
            FROM apply_queue
            WHERE updated_at >= ? AND updated_at IS NOT NULL
            GROUP BY CAST(updated_at AS DATE)
            ORDER BY CAST(updated_at AS DATE) ASC
        """, (since,)).fetchall()
        return [dict(r) for r in rows] if rows else []


def get_ai_usage_stats() -> dict:
    """AI generation usage metrics for the dashboard."""
    with get_db() as conn:
        def q1(sql, params=()):
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else {}

        totals = q1("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN provider = 'gemini'   THEN 1 ELSE 0 END) as gemini,
                   SUM(CASE WHEN provider = 'fallback' THEN 1 ELSE 0 END) as fallback
            FROM ai_generations
        """)
        today_count = (q1(
            "SELECT COUNT(*) as cnt FROM ai_generations WHERE date(created_at) = date('now')"
        ).get("cnt") or 0)

        by_type = conn.execute("""
            SELECT generation_type, COUNT(*) as cnt
            FROM ai_generations
            GROUP BY generation_type ORDER BY cnt DESC
        """).fetchall()

        return {
            "total_generations": totals.get("total") or 0,
            "gemini_calls":      totals.get("gemini") or 0,
            "fallback_calls":    totals.get("fallback") or 0,
            "today_calls":       today_count,
            "by_type":           [dict(r) for r in (by_type or [])],
        }


def save_snapshot(metric_name: str, metric_value: float, dimension: str = None):
    """Persist a metric snapshot row for historical analytics tracking."""
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO analytics_snapshots (metric_name, metric_value, dimension) VALUES (?,?,?)",
                (metric_name, metric_value, dimension)
            )
    except Exception as exc:
        log.warning("Failed to save analytics snapshot: %s", exc)


def take_daily_snapshot():
    """Called by a periodic Celery beat task to snapshot KPIs each day."""
    metrics = get_overview_metrics()
    for key, val in metrics.items():
        if isinstance(val, (int, float)):
            save_snapshot(key, float(val))
    log.info("Daily analytics snapshot saved.")
