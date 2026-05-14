web: gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 src.finder.api.main:app
worker: celery -A finder.shared.celery_app worker --loglevel=info --concurrency=1
