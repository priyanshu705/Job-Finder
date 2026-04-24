"""
src/finder/shared/logger.py
--------------------------
Centralized structured JSON logger for all Finder modules.
"""

import logging
import json
import os
import traceback
from datetime import datetime, timezone

from finder.shared.config import LOGS_DIR

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "ts":     datetime.now(timezone.utc).isoformat(),
            "level":  record.levelname,
            "module": record.name,
            "msg":    record.getMessage(),
        }
        if record.exc_info:
            log_obj["trace"] = traceback.format_exc()
        return json.dumps(log_obj)

class HumanFormatter(logging.Formatter):
    COLORS = {
        "DEBUG":    "\033[36m",
        "INFO":     "\033[32m",
        "WARNING":  "\033[33m",
        "ERROR":    "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        ts    = datetime.now().strftime("%H:%M:%S")
        return (
            f"{color}[{ts}][{record.name}][{record.levelname}]{self.RESET} "
            f"{record.getMessage()}"
        )

def get_logger(name: str) -> logging.Logger:
    os.makedirs(LOGS_DIR, exist_ok=True)
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # JSON file handler
    log_file = os.path.join(LOGS_DIR, f"{name}.jsonl")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(JSONFormatter())

    # Console handler
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(HumanFormatter())

    logger.addHandler(fh)
    logger.addHandler(sh)

    return logger

def screenshot_name(module: str, reason: str, context: str = "") -> str:
    ts  = int(datetime.now().timestamp())
    ctx = context[:20].replace("/", "_").replace("?", "").replace(" ", "_") if context else ""
    parts = [p for p in [module, reason, ctx, str(ts)] if p]
    return "_".join(parts)
