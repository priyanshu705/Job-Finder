"""
Playwright browser/process safety helpers.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


def close_quietly(obj: Any) -> None:
    if not obj:
        return
    try:
        obj.close()
    except Exception:
        pass


def reap_orphan_browser_children() -> int:
    """
    Best-effort cleanup for child Chromium/Chrome processes launched by this worker.
    Only touches child processes of current PID.
    """
    try:
        import psutil
    except Exception:
        return 0

    killed = 0
    try:
        current = psutil.Process()
        for child in current.children(recursive=True):
            try:
                name = (child.name() or "").lower()
                cmd = " ".join(child.cmdline()).lower()
                if any(tok in name for tok in ("chrome", "chromium", "msedge")) or "playwright" in cmd:
                    child.kill()
                    killed += 1
            except Exception:
                continue
    except Exception as exc:
        log.debug("Could not reap browser child processes: %s", exc)
    return killed

