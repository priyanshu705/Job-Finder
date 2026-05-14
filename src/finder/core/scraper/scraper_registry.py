"""
src/finder/core/scraper/scraper_registry.py
-------------------------------------------
Phase D: Scraper Registry
Dynamically resolves scraper classes and controls the multi-platform expansion.
"""

import logging
from typing import Dict, Type
from finder.core.scraper.base_scraper import BaseScraper

log = logging.getLogger("scraper_registry")

_REGISTRY: Dict[str, Type[BaseScraper]] = {}

def register_scraper(scraper_class: Type[BaseScraper]):
    """Decorator or function to register a scraper implementation."""
    instance = scraper_class()
    platform = instance.platform_name
    _REGISTRY[platform] = scraper_class
    log.info(f"Registered scraper: {platform}")
    return scraper_class

def get_scraper(platform: str) -> BaseScraper:
    """Instantiate and return the scraper for a given platform."""
    if platform not in _REGISTRY:
        raise ValueError(f"No scraper registered for platform: {platform}")
    return _REGISTRY[platform]()

def get_active_platforms() -> list[str]:
    """Return a list of all supported platforms."""
    return list(_REGISTRY.keys())
