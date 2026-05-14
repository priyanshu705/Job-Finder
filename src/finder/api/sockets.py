"""
src/finder/api/sockets.py
-------------------------
Flask-SocketIO integration. Uses Redis as the message queue
so that Celery background workers can emit events to connected clients.
"""
import os
from flask_socketio import SocketIO
from finder.shared.config import FUTURE_REDIS_URL
from finder.shared.logging import get_logger

log = get_logger("sockets")

redis_url = os.getenv("REDIS_URL", FUTURE_REDIS_URL or "redis://localhost:6379/0")

socketio = SocketIO(
    cors_allowed_origins="*",
    message_queue=redis_url,
    async_mode='eventlet'
)

def emit_event(event_name: str, data: dict = None):
    """
    Helper function to safely emit an event to all connected clients.
    Can be called from Celery workers because SocketIO is configured with a message_queue.
    """
    try:
        socketio.emit(event_name, data or {})
    except Exception as e:
        log.error("Failed to emit socket event '%s': %s", event_name, e)

@socketio.on('connect')
def handle_connect():
    log.info("Client connected to Socket.IO")

@socketio.on('disconnect')
def handle_disconnect():
    log.info("Client disconnected from Socket.IO")
