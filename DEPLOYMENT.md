# Railway Native Deployment

## Build Command
`pip install -r requirements.txt && python -m playwright install --with-deps chromium`

## Start Commands
- Backend: `gunicorn app:app`
- Worker: `celery -A celery_worker.celery worker --loglevel=info --pool=solo --concurrency=1`

## Required Services
- PostgreSQL
- Redis

## Required Environment Variables
- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `PYTHONPATH=src`
- `FLASK_DEBUG=0`
- `CORS_ORIGINS`
- `PLAYWRIGHT_BROWSERS_PATH=0`
- `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=false`
- `CELERY_VISIBILITY_TIMEOUT=3600`
- `CELERY_SOCKET_TIMEOUT=30`
- `CELERY_SOCKET_CONNECT_TIMEOUT=10`
- `CELERY_MAX_TASKS_PER_CHILD=100`
- `CELERY_MAX_MEMORY_PER_CHILD_KB=512000`
- `WORKER_MEMORY_PANIC_MB=900`
- `STALE_TASK_MINUTES=30`

## Deploy Checklist
1. Provision PostgreSQL and Redis in Railway.
2. Set all environment variables.
3. Configure build command.
4. Create backend service with backend start command.
5. Create worker service with worker start command.
6. Verify `/api/health`, `/api/health/redis`, `/api/health/celery`.
7. Trigger one task and confirm task_status transitions `queued -> running -> completed`.
8. Run one Playwright flow and verify no orphan Chromium growth.

