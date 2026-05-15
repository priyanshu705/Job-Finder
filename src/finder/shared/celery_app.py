"""
src/finder/shared/celery_app.py
-------------------------------
Celery application factory and configuration.
Uses Redis as both broker and backend.
"""
import os
from celery import Celery
from finder.shared.config import FUTURE_REDIS_URL

def make_celery(app_name=__name__):
    redis_url = os.getenv("REDIS_URL", FUTURE_REDIS_URL or "redis://localhost:6379/0")
    
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
        ]
    )
    
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        # Resilience settings
        broker_connection_retry_on_startup=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_track_started=True,
        worker_cancel_long_running_tasks_on_connection_loss=True,
        broker_transport_options={
            # Re-queue unacked tasks if a worker disappears.
            "visibility_timeout": int(os.getenv("CELERY_VISIBILITY_TIMEOUT", "3600")),
            "socket_timeout": int(os.getenv("CELERY_SOCKET_TIMEOUT", "30")),
            "socket_connect_timeout": int(os.getenv("CELERY_SOCKET_CONNECT_TIMEOUT", "10")),
        },
        # Performance
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=int(os.getenv("CELERY_MAX_TASKS_PER_CHILD", "100")),
        worker_max_memory_per_child=int(os.getenv("CELERY_MAX_MEMORY_PER_CHILD_KB", "512000")),
    )
    
    return celery

celery_app = make_celery("finder")
