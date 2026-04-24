"""
src/finder/shared/metrics.py
----------------------------
Lightweight JSONL-based metrics collector.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from finder.shared.logger import get_logger

log = get_logger("metrics")

from finder.shared.config import LOGS_DIR
METRICS_FILE = os.path.join(LOGS_DIR, "metrics.jsonl")

def record_metric(event: str, module: str, value: float = 1.0, meta: dict = None):
    os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
    entry = {
        "ts":     datetime.now(timezone.utc).isoformat(),
        "event":  event,
        "module": module,
        "value":  value,
        "meta":   meta or {},
    }
    try:
        with open(METRICS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        log.warning(f"Metrics write failed: {exc}")

def get_summary(hours: int = 24) -> dict:
    if not os.path.exists(METRICS_FILE):
        return {"error": "No metrics file yet — run the system first"}

    since  = datetime.now(timezone.utc) - timedelta(hours=hours)
    events: dict = {}

    with open(METRICS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                ts = datetime.fromisoformat(e["ts"])
                if ts > since:
                    key = e["event"]
                    events[key] = events.get(key, 0) + e.get("value", 1)
            except Exception:
                pass

    total_applies = (
        events.get("apply_success", 0)
        + events.get("apply_failed", 0)
        + events.get("apply_uncertain", 0)
    )

    return {
        "period_hours":    hours,
        "scrapes_run":     int(events.get("scrape_complete", 0)),
        "jobs_scraped":    int(events.get("jobs_scraped", 0)),
        "applies_success": int(events.get("apply_success", 0)),
        "applies_failed":  int(events.get("apply_failed", 0)),
        "applies_skipped": int(events.get("apply_skipped", 0)),
        "applies_uncertain":int(events.get("apply_uncertain", 0)),
        "total_applies":   total_applies,
        "success_rate":    f"{events.get('apply_success', 0) / max(total_applies, 1) * 100:.1f}%",
        "blocks_detected": int(events.get("block_detected", 0)),
        "sheets_failures": int(events.get("sheets_failed", 0)),
        "hitl_triggers":   int(events.get("hitl_triggered", 0)),
    }
