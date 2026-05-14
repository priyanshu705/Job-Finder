"""
src/finder/core/scraper/fingerprint.py
--------------------------------------
Phase D: Scraper Fingerprint Randomization
Implements lightweight anti-detection behavior by randomizing user agents,
viewport sizes, timezones, and language headers.
"""

import random

# Lightweight list of modern user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1366, "height": 768},
]

TIMEZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Los_Angeles",
    "Europe/London",
    "Asia/Kolkata",
]

LOCALES = [
    "en-US",
    "en-GB",
    "en-CA",
    "en-AU",
    "en-IN"
]

def get_random_fingerprint() -> dict:
    """Returns a dictionary of Playwright context options for lightweight randomization."""
    return {
        "user_agent": random.choice(USER_AGENTS),
        "viewport": random.choice(VIEWPORTS),
        "timezone_id": random.choice(TIMEZONES),
        "locale": random.choice(LOCALES),
        "java_script_enabled": True,
        "bypass_csp": True,
    }
