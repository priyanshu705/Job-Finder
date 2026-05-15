"""
src/finder/shared/celery_app.py
-------------------------------
Celery application factory and configuration.
Uses Redis as both broker and backend.
"""
import logging
import os
import sys
from celery import Celery
from celery.signals import task_failure, task_retry, worker_process_init, worker_shutdown
from finder.shared.config import FUTURE_REDIS_URL

logger = logging.getLogger("finder.celery")


def _register_signals(celery: Celery) -> None:
    @worker_process_init.connect(sender=celery)
    def on_worker_init(**kwargs):
        pid = os.getpid()
        logger.info("Celery worker init pid=%s", pid)
        try:
            import psutil
            proc = psutil.Process(pid)
            rss_mb = proc.memory_info().rss // 1024 // 1024
            logger.info("Celery worker memory at init: %s MB", rss_mb)
        except Exception as exc:
            logger.debug("Could not probe worker memory at init: %s", exc)

    @worker_shutdown.connect(sender=celery)
    def on_worker_shutdown(**kwargs):
        logger.warning("Celery worker shutdown: %s", kwargs)

    @task_failure.connect(sender=celery)
    def on_task_failure(task_id=None, exception=None, args=None, kwargs=None, einfo=None, sender=None, **_):
        logger.error(
            "Celery task failure task_id=%s task=%s exception=%s",
            task_id,
            sender.name if sender else None,
            exception,
        )
        if einfo:
            logger.debug("Celery task failure traceback: %s", einfo)

    @task_retry.connect(sender=celery)
    def on_task_retry(request=None, reason=None, einfo=None, **_):
        logger.warning(
            "Celery task retry task_id=%s reason=%s",
            getattr(request, "id", None),
            reason,
        )


def make_celery(app_name=__name__):
    redis_url = os.getenv("REDIS_URL", FUTURE_REDIS_URL) or "redis://localhost:6379/0"

    celery = Celery(
        app_name,
        broker=redis_url,
        backend=redis_url,
        include=[
            "finder.core.tasks.agent_tasks",
            "finder.core.tasks.ai_tasks",
            "finder.core.tasks.analytics_tasks",
            "finder.core.tasks.intelligence_tasks",
            "finder.core.tasks.cleanup_tasks",
            "finder.core.tasks.interview_tasks",
        ],
    )

    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        broker_connection_retry_on_startup=True,
        broker_connection_retry=True,
        broker_connection_max_retries=int(os.getenv("CELERY_BROKER_MAX_RETRIES", "10")),
        broker_connection_timeout=int(os.getenv("CELERY_BROKER_CONNECT_TIMEOUT", "10")),
        task_publish_retry=True,
        task_publish_retry_policy={
            "max_retries": int(os.getenv("CELERY_PUBLISH_MAX_RETRIES", "3")),
            "interval_start": 0.1,
            "interval_step": 0.2,
            "interval_max": 0.5,
        },
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_track_started=True,
        worker_cancel_long_running_tasks_on_connection_loss=True,
        worker_prefetch_multiplier=1,
        worker_disable_rate_limits=True,
        worker_max_tasks_per_child=int(os.getenv("CELERY_MAX_TASKS_PER_CHILD", "100")),
        worker_max_memory_per_child=int(os.getenv("CELERY_MAX_MEMORY_PER_CHILD_KB", "512000")),
        task_default_rate_limit="1000/m",
        broker_transport_options={
            "visibility_timeout": int(os.getenv("CELERY_VISIBILITY_TIMEOUT", "3600")),
            "socket_timeout": int(os.getenv("CELERY_SOCKET_TIMEOUT", "30")),
            "socket_connect_timeout": int(os.getenv("CELERY_SOCKET_CONNECT_TIMEOUT", "10")),
        },
    )

    _register_signals(celery)
    return celery


celery_app = make_celery("finder")
