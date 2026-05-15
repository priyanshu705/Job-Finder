web: gunicorn app:app
worker: celery -A celery_worker.celery worker --loglevel=info --pool=solo --concurrency=1
