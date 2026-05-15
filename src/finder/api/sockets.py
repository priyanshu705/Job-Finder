"""
src/finder/api/sockets.py
-------------------------
Compatibility shim for legacy emit_event calls.

WebSocket transport was removed for Railway-native deployment stability.
Event emits are intentionally no-op and debug-logged only.
"""
from finder.shared.logging import get_logger

log = get_logger("sockets")


def emit_event(event_name: str, data: dict = None):
    """No-op event emitter kept for backward compatibility with task modules."""
    log.debug("event:%s payload=%s", event_name, data or {})
