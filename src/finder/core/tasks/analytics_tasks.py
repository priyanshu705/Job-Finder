"""
src/finder/core/tasks/analytics_tasks.py
-----------------------------------------
Celery tasks for periodic analytics snapshots.
"""

import logging
from finder.shared.celery_app import celery_app
from finder.core.analytics.service import compute_kpis

log = logging.getLogger(__name__)


@celery_app.task(name="analytics.snapshot", bind=True, max_retries=2)
def task_analytics_snapshot(self):
    """Compute and persist an analytics snapshot to analytics_snapshots table."""
    try:
        log.info("Analytics snapshot task started")
        kpis = compute_kpis()
        log.info("Analytics snapshot computed: %s", kpis)
        return {"status": "ok", "kpis": kpis}
    except Exception as exc:
        log.error("Analytics snapshot failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)
