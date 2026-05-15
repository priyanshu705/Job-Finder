#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"
python scripts/check_python_version.py
exec celery -A celery_worker.celery worker --loglevel=info --pool=solo --concurrency=1 --prefetch-multiplier=1 --without-gossip --without-mingle
