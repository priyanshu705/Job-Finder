web: python scripts/check_python_version.py && gunicorn app:app
worker: python scripts/check_python_version.py && celery -A celery_worker.celery worker --loglevel=info --pool=solo --concurrency=1 --prefetch-multiplier=1 --without-gossip --without-mingle
