"""
src/finder/core/scraper/base_scraper.py
---------------------------------------
Phase D: Modular Base Scraper Interface
Defines the standard contract for all platform discovery scrapers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseScraper(ABC):
    """
    Abstract base class for all job discovery scrapers.
    Forces normalization and predictable safety mechanisms.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the unique identifier for the platform (e.g., 'linkedin')."""
        pass

    @abstractmethod
    def authenticate(self, page) -> bool:
        """
        Ensure the session is authenticated.
        Implementations should use the Playwright page object and encrypted session storage.
        Return True if authenticated, False otherwise.
        """
        pass

    @abstractmethod
    def search_jobs(self, page, query: str, location: str, limit: int = 10) -> List[str]:
        """
        Perform a search query and return a list of discovered job URLs.
        Must handle pagination and graceful degradation on CAPTCHAs.
        """
        pass

    @abstractmethod
    def parse_job(self, page, job_url: str) -> Optional[Dict[str, Any]]:
        """
        Navigate to a specific job URL and parse its raw data.
        Return raw unnormalized data.
        """
        pass

    def normalize_job(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalize raw parsed data into the unified schema:
        {
            "title": str,
            "company": str,
            "location": str,
            "description": str,
            "apply_url": str,
            "source": str,
            "easy_apply": bool
        }
        """
        if not raw_data:
            return None

        # Base implementation, can be overridden if needed
        return {
            "title": raw_data.get("title", "Unknown Role").strip(),
            "company": raw_data.get("company", "Unknown Company").strip(),
            "location": raw_data.get("location", "").strip(),
            "description": raw_data.get("description", "").strip(),
            "apply_url": raw_data.get("apply_url", "").strip(),
            "source": self.platform_name,
            "easy_apply": bool(raw_data.get("easy_apply", False)),
        }
