"""
src/finder/shared/retry.py
--------------------------
Reusable retry decorator with exponential backoff.
"""

import time
import functools
from finder.shared.logger import get_logger

def retry(
    max_attempts: int = 3,
    delay: float = 2.0,
    exceptions: tuple = (Exception,),
    log_name: str = "retry",
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(log_name)
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    wait = delay * attempt
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {exc}"
                        )
                        raise
                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {exc}. "
                        f"Retrying in {wait:.1f}s..."
                    )
                    time.sleep(wait)
            return None
        return wrapper
    return decorator
