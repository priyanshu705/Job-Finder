"""
src/finder/core/scraper/discovery.py
------------------------------------
Phase D: Scraper Entrypoint
Runs the modular multi-platform discovery scrapers.
"""

import logging
from playwright.sync_api import sync_playwright
from finder.core.scraper.scraper_registry import get_active_platforms, get_scraper
from finder.core.scraper.session_manager import load_encrypted_session, save_encrypted_session
from finder.core.scraper.health import SourceHealthTracker
from finder.core.scraper.normalization import canonicalize_url
from finder.core.scraper.fingerprint import get_random_fingerprint
from finder.shared.database import get_db

log = logging.getLogger("discovery")

def run_discovery_scrapers(headless: bool = True):
    """
    Executes the discovery scraping cycle.
    Uses Playwright locally within the Celery worker (concurrency=1 assumed).
    """
    from finder.shared.feature_flags import is_feature_enabled
    if not is_feature_enabled("PLAYWRIGHT", default=True):
        log.warning("Playwright scrapers disabled via feature flag. Skipping.")
        return {"status": "skipped", "reason": "feature_flag_disabled"}

    platforms = get_active_platforms()
    if not platforms:
        log.warning("No discovery scrapers registered. Skipping.")
        return {"status": "skipped", "reason": "no_platforms"}

    results = {}
    with sync_playwright() as p:
        for platform in platforms:
            scraper = get_scraper(platform)
            log.info(f"Starting discovery scraper for {platform}")

            # 1. Prepare secure fingerprint and context
            fp = get_random_fingerprint()
            browser = p.chromium.launch(headless=headless, args=["--disable-blink-features=AutomationControlled"])
            
            # Load encrypted storage state if available
            user_id = 1 # Assume default single-tenant user for MVP
            storage_state = load_encrypted_session(user_id, platform)
            
            from finder.core.scraper.proxy import ProxyProvider
            
            proxy_config = ProxyProvider.get_proxy()
            
            context_kwargs = {
                "user_agent": fp["user_agent"],
                "viewport": fp["viewport"],
                "timezone_id": fp["timezone_id"],
                "locale": fp["locale"],
                "bypass_csp": True,
            }
            if proxy_config:
                context_kwargs["proxy"] = proxy_config
                
            if storage_state:
                context = browser.new_context(storage_state=storage_state, **context_kwargs)
            else:
                context = browser.new_context(**context_kwargs)

            page = context.new_page()

            # 2. Authenticate
            is_auth = scraper.authenticate(page)
            if not is_auth:
                log.warning(f"Failed to authenticate on {platform}. Proceeding with public scrape if possible.")

            # 3. Discovery Search
            queries = ["Software Engineer", "Backend Developer"]
            locations = ["Remote"]
            
            total_jobs_found = 0
            start_time = __import__('time').time()
            
            try:
                for query in queries:
                    for loc in locations:
                        urls = scraper.search_jobs(page, query, loc, limit=5)
                        
                        for url in urls:
                            # 4. Canonicalize
                            clean_url = canonicalize_url(url, platform)
                            
                            with get_db() as conn:
                                existing = conn.execute("SELECT id FROM jobs WHERE job_url = ?", (clean_url,)).fetchone()
                                if existing:
                                    continue
                                
                            # 5. Parse Job
                            raw_job = scraper.parse_job(page, url)
                            if raw_job:
                                norm_job = scraper.normalize_job(raw_job)
                                if norm_job:
                                    norm_job["job_url"] = clean_url
                                    
                                    with get_db() as conn:
                                        conn.execute(
                                            "INSERT INTO jobs (user_id, title, company, location, description, job_url, platform, form_type) "
                                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                            (user_id, norm_job["title"], norm_job["company"], norm_job["location"], norm_job["description"], clean_url, platform, "easy_apply" if norm_job["easy_apply"] else "standard")
                                        )
                                        conn.execute(
                                            "INSERT INTO apply_queue (user_id, job_url, status) VALUES (?, ?, 'pending')",
                                            (user_id, clean_url)
                                        )
                                    total_jobs_found += 1
            except Exception as exc:
                log.error(f"Scrape cycle failed for {platform}: {exc}")
                SourceHealthTracker.record_scrape(platform, success=False)
            finally:
                # 6. Save encrypted session back
                try:
                    state = context.storage_state()
                    save_encrypted_session(user_id, platform, state)
                except Exception as exc:
                    log.warning(f"Could not save session state: {exc}")
                    
                duration = __import__('time').time() - start_time
                SourceHealthTracker.record_scrape(platform, success=True, jobs_found=total_jobs_found, duration_seconds=duration)
                
                context.close()
                browser.close()
                
            results[platform] = {"jobs_found": total_jobs_found}
            
    return {"status": "success", "platforms": results}
