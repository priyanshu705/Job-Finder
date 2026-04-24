"""
src/finder/core/scraper/service.py
---------------------------------
Internshala job scraper — Finder V6.
"""

import os
import json
import time
import re
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from playwright.sync_api import (
    sync_playwright,
    Page,
    Browser,
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
)
from bs4 import BeautifulSoup

from finder.shared.logger import get_logger, screenshot_name
from finder.shared.database import get_db
from finder.shared.retry import retry

load_dotenv()

log = get_logger("scraper")

EMAIL     = os.getenv("INTERNSHALA_EMAIL", "")
PASSWORD  = os.getenv("INTERNSHALA_PASSWORD", "")
QUERY     = os.getenv("SEARCH_QUERY", "python developer")
PLATFORM  = "internshala"

BASE_URL       = "https://internshala.com"
LOGIN_URL      = f"{BASE_URL}/login"
JOBS_SEARCH    = f"{BASE_URL}/jobs/keywords-{{}}"
MAX_PAGES      = int(os.getenv("SCRAPER_MAX_PAGES", "5"))
HEADLESS       = os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"
SLOW_MO        = int(os.getenv("SCRAPER_SLOW_MO", "0"))

from finder.shared.config import SCREENSHOT_DIR

def _slug(query: str) -> str:
    return query.strip().lower().replace(" ", "-")

def _save_screenshot(page: Page, module: str, reason: str, context: str = "") -> None:
    name = screenshot_name(module, reason, context)
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    try:
        page.screenshot(path=path)
        log.debug(f"Screenshot saved: {path}")
    except Exception as e:
        log.warning(f"Could not save screenshot: {e}")

def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def is_logged_in(page: Page) -> bool:
    """Checks if the user is already authenticated on the current page."""
    try:
        # Check for indicators of a logged-in state
        indicators = ["#navbar-user-dropdown", ".navbar-avatar", "a[href*='/dashboard']"]
        for sel in indicators:
            if page.locator(sel).is_visible():
                return True
    except Exception:
        pass
    return False

def login(page: Page) -> bool:
    if is_logged_in(page):
        log.info("Already authenticated. Skipping login flow.")
        return True

    log.info("Navigating to Internshala login...")
    try:
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_selector(
            "#modal-login-email, input[name='email'], input[type='email']",
            timeout=25_000,
        )
    except PlaywrightTimeoutError:
        _save_screenshot(page, "scraper", "login_page_timeout")
        log.error("Login page did not load in time.")
        return False

    try:
        email_sel = "#modal-login-email" if page.query_selector("#modal-login-email") else "input[name='email'], input[type='email']"
        pass_sel = "#modal-login-password" if page.query_selector("#modal-login-password") else "input[name='password'], input[type='password']"
        page.fill(email_sel, EMAIL)
        page.fill(pass_sel, PASSWORD)
        page.click("input[type='submit'], button[type='submit']")
    except Exception as exc:
        _save_screenshot(page, "scraper", "login_fill_error")
        log.error(f"Could not fill/submit login form: {exc}")
        return False

    deadline = time.time() + 45
    while time.time() < deadline:
        try:
            current_url = page.url
            if "login" not in current_url:
                log.info(f"Login successful — redirected to: {current_url}")
                return True
            for selector in ["#navbar-user-dropdown", ".navbar-avatar", "a[href*='/dashboard']"]:
                if page.query_selector(selector):
                    log.info(f"Login successful — detected: {selector}")
                    return True
        except Exception:
            pass
        time.sleep(1.5)
    return False

def _parse_job_card(card_soup: BeautifulSoup) -> Optional[dict]:
    try:
        link_tag = card_soup.select_one("a.job-title-href, a[href*='/jobs/']")
        if not link_tag: return None
        href = link_tag.get("href", "")
        if not href.startswith("http"): href = BASE_URL + href
        job_url = href.split("?")[0]
        title_tag = card_soup.select_one(".job-internship-name, .profile, h3.job-title")
        title = _clean_text(title_tag.get_text()) if title_tag else _clean_text(link_tag.get_text())
        company_tag = card_soup.select_one(".company-name")
        company = _clean_text(company_tag.get_text()) if company_tag else "Unknown"
        return {
            "title": title, "company": company, "platform": PLATFORM,
            "location": _clean_text(card_soup.select_one(".location").get_text()) if card_soup.select_one(".location") else "",
            "salary": _clean_text(card_soup.select_one(".stipend").get_text()) if card_soup.select_one(".stipend") else "",
            "posted_at": "", "job_url": job_url, "description": "", "skills": "", "form_type": "unknown",
        }
    except Exception: return None

@retry(max_attempts=2, delay=3.0, log_name="scraper")
def _fetch_job_detail(page: Page, job: dict) -> dict:
    try:
        page.goto(job["job_url"], wait_until="domcontentloaded", timeout=25_000)
        time.sleep(1.2)
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        desc_tag = soup.select_one(".internship-details, .job-description, .about-job")
        job["description"] = _clean_text(desc_tag.get_text()) if desc_tag else ""
        skill_tags = soup.select(".round_tabs span, .tags span, .skills-tag")
        skills_list = [_clean_text(s.get_text()) for s in skill_tags if s.get_text(strip=True)]
        job["skills"] = ", ".join(dict.fromkeys(skills_list))
        apply_btn = soup.select_one("button#apply-button, a#apply-button")
        btn_text = _clean_text(apply_btn.get_text()).lower() if apply_btn else ""
        job["form_type"] = "easy_apply" if "easy" in btn_text or "apply now" in btn_text else "external" if apply_btn else "unknown"
        return job
    except Exception: return job

def _get_existing_urls() -> set:
    with get_db() as conn:
        rows = conn.execute("SELECT job_url FROM jobs").fetchall()
    return {r["job_url"] for r in rows}

def _insert_job(job: dict) -> bool:
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO jobs (title, company, platform, location, description, skills, salary, posted_at, job_url, form_type, scraped_at) VALUES (:title, :company, :platform, :location, :description, :skills, :salary, :posted_at, :job_url, :form_type, :scraped_at)",
                {**job, "scraped_at": datetime.now(timezone.utc).isoformat()}
            )
        return True
    except Exception: return False

def _enqueue_job(job: dict) -> bool:
    try:
        with get_db() as conn:
            conn.execute("INSERT OR IGNORE INTO apply_queue (job_url, job_json, status, queued_at) VALUES (?, ?, 'pending', ?)",
                (job["job_url"], json.dumps(job), datetime.now(timezone.utc).isoformat()))
        return True
    except Exception: return False

def _scrape_page(page: Page, page_num: int, slug: str) -> list[dict]:
    url = JOBS_SEARCH.format(slug) if page_num == 1 else f"{BASE_URL}/jobs/keywords-{slug}/page-{page_num}"
    log.info(f"Scraping page {page_num}: {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        time.sleep(1.5)
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".individual_internship")
        return [j for j in (_parse_job_card(c) for c in cards) if j]
    except Exception: return []

def run_scraper(query: str = "", max_pages: int = 0, headless: bool = True, deadline: float = 0.0, page: Optional[Page] = None) -> dict:
    search_query = query or QUERY
    pages = max_pages or MAX_PAGES
    slug = _slug(search_query)
    stats = {"scraped": 0, "new_jobs": 0, "enqueued": 0, "skipped": 0, "errors": 0, "timed_out": False, "query": search_query, "pages": pages, "started_at": datetime.now(timezone.utc).isoformat()}
    
    if deadline > 0 and time.time() > deadline:
        stats["timed_out"] = True
        return stats

    log.info(f"Starting scraper | query='{search_query}' | max_pages={pages}")

    # Helper to run the core scraper logic
    def _run_with_page(p: Page, context):
        if not page and not login(p): # Only login if we created the page ourselves
            stats["errors"] += 1
            return
            
        existing_urls = _get_existing_urls()
        all_jobs = []
        for pg in range(1, pages + 1):
            if deadline > 0 and time.time() > deadline:
                stats["timed_out"] = True
                break
            page_jobs = _scrape_page(p, pg, slug)
            if not page_jobs: break
            all_jobs.extend(page_jobs)
            time.sleep(1.0)

        stats["scraped"] = len(all_jobs)
        # Use a separate page for details if possible, otherwise use the same
        detail_page = context.new_page() if context else p
        for job in all_jobs:
            if deadline > 0 and time.time() > deadline:
                stats["timed_out"] = True
                break
            if job["job_url"] in existing_urls:
                stats["skipped"] += 1
                continue
            job = _fetch_job_detail(detail_page, job)
            if _insert_job(job):
                stats["new_jobs"] += 1
                if _enqueue_job(job): stats["enqueued"] += 1
            else: stats["skipped"] += 1
            time.sleep(0.8)
        
        if context and detail_page != p:
            detail_page.close()

    if page:
        log.info("Reusing existing session for scraper.")
        _run_with_page(page, page.context)
    else:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless, slow_mo=SLOW_MO, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(user_agent="Mozilla/5.0 ...", viewport={"width": 1280, "height": 800})
            p = context.new_page()
            _run_with_page(p, context)
            browser.close()

    stats["finished_at"] = datetime.now(timezone.utc).isoformat()
    return stats
