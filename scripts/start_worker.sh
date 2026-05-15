#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"
exec celery -A celery_worker.celery worker --loglevel=info --pool=solo --concurrency=1
