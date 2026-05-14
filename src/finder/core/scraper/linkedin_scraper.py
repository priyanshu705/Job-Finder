"""
src/finder/core/scraper/linkedin_scraper.py
-------------------------------------------
Phase D: LinkedIn Discovery Scraper
Implements the base scraper interface for LinkedIn job discovery.
STRICTLY read-only discovery. No auto-applying.
"""

import logging
from typing import List, Dict, Any, Optional
from finder.core.scraper.base_scraper import BaseScraper
from finder.core.scraper.safety import RateLimiter, CooldownManager
from finder.api.sockets import emit_event

log = logging.getLogger("linkedin_scraper")

class LinkedInScraper(BaseScraper):
    @property
    def platform_name(self) -> str:
        return "linkedin"

    def authenticate(self, page) -> bool:
        """
        Authenticate with LinkedIn. Assumes session_manager has already injected storage_state
        if available. We just verify authentication status.
        """
        try:
            log.info("Verifying LinkedIn authentication...")
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            RateLimiter.wait_safe(2.0, 4.0)
            
            # Check if we are redirected to login or if feed elements exist
            if "login" in page.url or "checkpoint" in page.url:
                log.warning("LinkedIn session expired or invalid. Manual re-login required.")
                CooldownManager.set_cooldown(self.platform_name, 60, "Session Expired/CAPTCHA")
                return False
                
            return True
        except Exception as exc:
            log.error(f"Error during LinkedIn auth verification: {exc}")
            return False

    def search_jobs(self, page, query: str, location: str, limit: int = 10) -> List[str]:
        """
        Search for jobs and return a list of URLs.
        """
        job_urls = []
        if CooldownManager.is_on_cooldown(self.platform_name):
            log.warning(f"{self.platform_name} is on cooldown. Skipping search.")
            return job_urls

        try:
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location={location}"
            page.goto(search_url, wait_until="domcontentloaded")
            RateLimiter.wait_safe(3.0, 6.0)
            
            emit_event("scraper:progress", {"platform": self.platform_name, "status": "searching", "query": query})

            # Check for ban/captcha
            if "authwall" in page.url or "captcha" in page.content().lower():
                CooldownManager.set_cooldown(self.platform_name, 120, "CAPTCHA/Authwall detected")
                return job_urls

            from finder.core.scraper.snapshots import save_snapshot
            save_snapshot(self.platform_name, page.content(), "v1")

            # Extract job links (simplified example, real DOM depends on current LI structure)
            elements = page.locator("a.job-card-list__title").all()
            for el in elements[:limit]:
                href = el.get_attribute("href")
                if href:
                    # Normalize URL to remove tracking params
                    clean_url = href.split("?")[0]
                    if not clean_url.startswith("http"):
                        clean_url = f"https://www.linkedin.com{clean_url}"
                    job_urls.append(clean_url)
            
            log.info(f"LinkedIn discovery found {len(job_urls)} jobs.")
            return job_urls

        except Exception as exc:
            log.error(f"Error searching LinkedIn jobs: {exc}")
            return job_urls

    def parse_job(self, page, job_url: str) -> Optional[Dict[str, Any]]:
        """
        Navigate to job URL and extract details.
        """
        if CooldownManager.is_on_cooldown(self.platform_name):
            return None

        try:
            page.goto(job_url, wait_until="domcontentloaded")
            RateLimiter.wait_safe(2.0, 4.0)

            title = page.locator("h1.job-details-jobs-unified-top-card__job-title").text_content()
            company = page.locator("a.job-details-jobs-unified-top-card__company-name").text_content()
            location = page.locator("span.tvm__text--low-emphasis").first.text_content()
            description = page.locator("div.jobs-description__content").text_content()
            
            # Check for easy apply button presence
            easy_apply = page.locator("button.jobs-apply-button").count() > 0

            return {
                "title": title,
                "company": company,
                "location": location,
                "description": description,
                "apply_url": job_url,
                "easy_apply": easy_apply
            }
        except Exception as exc:
            log.warning(f"Failed to parse LinkedIn job {job_url}: {exc}")
            return None

# Auto-register this scraper
from finder.core.scraper.scraper_registry import register_scraper
register_scraper(LinkedInScraper)
