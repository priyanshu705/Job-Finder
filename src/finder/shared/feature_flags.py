"""
src/finder/shared/feature_flags.py
----------------------------------
Final Hardening: Scraper Feature Flags
Lightweight, environment-driven kill switches for safe production rollouts.
"""

import os
import logging

log = logging.getLogger("feature_flags")

def is_feature_enabled(feature_name: str, default: bool = False) -> bool:
    """
    Checks if a feature flag is enabled.
    Checks environment variables first, allowing instant kill switches.
    """
    env_val = os.getenv(f"FEATURE_{feature_name.upper()}")
    if env_val is not None:
        return env_val.lower() in ("true", "1", "yes")
        
    return default

def get_all_flags() -> dict:
    return {
        "LINKEDIN_DISCOVERY": is_feature_enabled("LINKEDIN_DISCOVERY", default=True),
        "SOURCE_HEALTH": is_feature_enabled("SOURCE_HEALTH", default=True),
        "MULTI_PLATFORM": is_feature_enabled("MULTI_PLATFORM", default=False),
        "PLAYWRIGHT": is_feature_enabled("PLAYWRIGHT", default=True),
    }
