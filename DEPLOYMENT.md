# Final Production Deployment

## Runtime enforcement
- `runtime.txt` is fixed to `python-3.11.9` for Railway and Render.
- `.python-version` is also added with `3.11.9` for local development compatibility.
- `scripts/check_python_version.py` validates the interpreter before startup.

## Build command
- `python scripts/check_python_version.py && pip install -r requirements.txt && python -m playwright install --with-deps chromium`

## Start commands
- Backend: `python scripts/check_python_version.py && gunicorn app:app`
- Worker: `python scripts/check_python_version.py && celery -A celery_worker.celery worker --loglevel=info --pool=solo --concurrency=1 --prefetch-multiplier=1 --without-gossip --without-mingle`

## Required services
- PostgreSQL
- Redis

## Required environment variables
- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `PYTHONPATH=src`
- `FLASK_DEBUG=0`
- `FLASK_ENV=production`
- `CORS_ORIGINS=*`
- `PLAYWRIGHT_BROWSERS_PATH=0`
- `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=false`
- `PLAYWRIGHT_LAUNCH_TIMEOUT_MS=60000`
- `PLAYWRIGHT_DEFAULT_TIMEOUT_MS=45000`
- `CELERY_VISIBILITY_TIMEOUT=3600`
- `CELERY_SOCKET_TIMEOUT=30`
- `CELERY_SOCKET_CONNECT_TIMEOUT=10`
- `CELERY_BROKER_MAX_RETRIES=10`
- `CELERY_BROKER_CONNECT_TIMEOUT=10`
- `CELERY_PUBLISH_MAX_RETRIES=3`
- `CELERY_MAX_TASKS_PER_CHILD=100`
- `CELERY_MAX_MEMORY_PER_CHILD_KB=512000`
- `WORKER_MEMORY_PANIC_MB=900`
- `STALE_TASK_MINUTES=30`

## Railway deployment notes
1. Create a Python service for the backend and a separate service for the Celery worker.
2. Use `PYTHONPATH=src` and set `FLASK_ENV=production`.
3. Use the build command above; Railway will install Chromium in the app container.
4. Keep worker concurrency at `1` with `--pool=solo` and `--prefetch-multiplier=1`.
5. Prefer `--without-gossip` and `--without-mingle` to reduce worker overhead.

## Render deployment notes
1. Render uses `render.yaml` which now enforces `python scripts/check_python_version.py` before both build and start.
2. Set the same environment variables as Railway.
3. Use a dedicated `web` service for Gunicorn and a second `web` service for Celery worker.
4. Confirm the `buildCommand` installs browsers with `python -m playwright install --with-deps chromium`.

## Cache-clear redeploy instructions
- Railway: redeploy with a clean build by clearing the build cache in the Railway project settings, then rebuild.
- Render: go to the service deploy settings and trigger a "Clear Build Cache" or "Redeploy Latest Commit".
- Local: remove `.pytest_cache`, `__pycache__`, `.venv`, and rerun `python -m venv .venv`.

## Playwright hardening
- Chromium is installed explicitly during build with `--with-deps chromium`.
- Headless launch uses sandbox-safe launch arguments and a 60-second startup timeout.
- Page and context default timeouts are set to `45000ms`.
- Browser, context, and page cleanup are already handled inside `run_agent_cycle()`.
- Orphan Chromium processes are reaped after each cycle.

## Celery production hardening
- `worker_prefetch_multiplier=1`
- `task_acks_late=True`
- `task_reject_on_worker_lost=True`
- `worker_max_tasks_per_child=100`
- `worker_max_memory_per_child=512000`
- `broker_connection_max_retries=10`
- `task_publish_retry` limited to 3 attempts
- `task_default_rate_limit=1000/m`
- Lightweight worker startup and shutdown logging is enabled.

## Final validation checklist
1. Confirm `runtime.txt` contains `python-3.11.9`.
2. Confirm `python scripts/check_python_version.py` passes.
3. Confirm `pip install -r requirements.txt` succeeds.
4. Confirm `python -m playwright install --with-deps chromium` succeeds.
5. Confirm `python scripts/check_python_version.py && gunicorn app:app` starts successfully.
6. Confirm `python scripts/check_python_version.py && celery -A celery_worker.celery worker --loglevel=info --pool=solo --concurrency=1 --prefetch-multiplier=1 --without-gossip --without-mingle` starts successfully.
7. Confirm `/api/health`, `/api/health/redis`, and `/api/health/celery` return healthy responses.
8. Confirm a Celery task enqueues, runs, and completes without retry storms.
9. Confirm one Playwright browser flow executes without orphan Chromium processes.

## Failure recovery guidance
- Deployment boot failure: verify Python version, check `runtime.txt`, and clear build cache.
- Redis disconnect: verify `REDIS_URL`, restart Redis service, and redeploy worker.
- PostgreSQL reconnect: verify `DATABASE_URL`, test with `psql`, and restart backend.
- Worker crash: inspect worker logs, ensure `--pool=solo`, and restart worker service.
- Playwright launch failure: verify Chromium installed, disable `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD`, and rerun the build.
- Memory spike: lower concurrency, enforce `WORKER_MEMORY_PANIC_MB`, and restart slow workers.
- Stuck pending tasks: inspect `/api/health/celery`, clear stale reserved jobs, restart worker.
- Chromium orphan buildup: verify `reap_orphan_browser_children()` is active and restart the service if orphan processes remain.

