"""
src/finder/core/agent/orchestrator.py
------------------------------------
Master orchestrator — Finder V6.
Handles the end-to-end cycle: Scrape -> Match -> Queue -> Apply.
"""

import os
import json
import time
import traceback
from datetime import datetime, timezone, timedelta, date

from finder.shared.logger import get_logger
from finder.shared.database import get_db, get_table_counts
from finder.shared.metrics import get_summary, record_metric

# Phase Imports
from finder.core.scraper import run_scraper
from finder.core.matcher import run_matcher
from finder.core.queue import run_queue
from finder.core.apply_bot import run_apply_assistant

# Intelligence Imports
from finder.core.intelligence.profile import get_profile_summary
from finder.core.intelligence.adaptive_search import get_weighted_queries, record_feedback

log = get_logger("agent")

def _get_controls():
    try:
        with get_db() as conn:
            return {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM user_controls").fetchall()}
    except Exception as e:
        log.error(f"Failed to fetch controls: {e}")
        return {}

def get_status():
    """Returns the current system status for dashboard use."""
    with get_db() as conn:
        q_rows = conn.execute("SELECT status, COUNT(*) as cnt FROM apply_queue GROUP BY status").fetchall()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db_counts": get_table_counts(),
        "queue": {r["status"]: r["cnt"] for r in q_rows},
        "controls": _get_controls(),
        "metrics_24h": get_summary(hours=24),
    }

from playwright.sync_api import sync_playwright
from finder.core.scraper.service import login as scraper_login

def run_agent_cycle(query="", scraper_pages=0, headless=True, report_callback=None):
    """
    Executes a full agent cycle using a single browser session.
    """
    def _report(phase, progress, msg=None):
        if report_callback:
            report_callback(phase, progress, msg)

    start_time = time.time()
    log.info("🚀 Starting Agent Cycle...")
    _report("init", "Initializing cycle...", "🚀 Starting Agent Cycle")
    
    controls = _get_controls()
    
    # 0. Check for Pause
    if controls.get("paused") == "true":
        log.warning("⏸ Agent is currently PAUSED via user controls. Exiting cycle.")
        _report("idle", "Agent is paused", "⏸ Agent is currently PAUSED")
        return {"status": "paused"}

    results = {
        "cycle_id": f"cycle_{int(start_time)}",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "scraper": {},
        "matcher": {},
        "queue": {},
        "apply_bot": {},
        "error": None
    }

    with sync_playwright() as pw:
        # Launch browser once
        log.info(f"Launching browser (headless={headless})...")
        _report("init", "Launching browser...", "Launching browser session")
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        try:
            # 1. Global Login
            log.info("Authenticating session...")
            _report("auth", "Authenticating...", "Authenticating platform session")
            if not scraper_login(page):
                log.error("❌ Authentication failed. Aborting cycle.")
                _report("auth", "Authentication failed", "❌ Authentication failed")
                results["error"] = "Authentication failed"
                return results
            
            log.info("✅ Session authenticated. Reusing for all phases.")
            _report("auth", "Authenticated", "✅ Session authenticated")

            # 2. Intelligence Check
            profile = get_profile_summary()
            queries = get_weighted_queries(limit=3)
            log.info(f"Generated intelligent queries: {[q['query'] for q in queries]}")
            _report("init", f"Targeting roles: {', '.join([q['query'] for q in queries])}")

            # 3. Scraper Phase (Adaptive Multi-Query)
            log.info("━━ Phase 1: Scraper ━━━━━━━━━━━━━━━━━━━━━━━━")
            _report("scraper", "Scraping jobs...", "━━ Phase 1: Scraper")
            results["scraper"]["total_found"] = 0
            
            for q_obj in queries:
                q_text = q_obj["query"]
                _report("scraper", f"Searching '{q_text}'...", f"Starting scraper | query='{q_text}'")
                try:
                    s_res = run_scraper(query=q_text, max_pages=2, page=page)
                    found = s_res.get("found", s_res.get("new_jobs", 0))
                    results["scraper"]["total_found"] += found
                    
                    # Feed back to adaptive search
                    if found > 0: record_feedback(q_text, success=True)
                    else: record_feedback(q_text, success=False)
                except Exception as e:
                    log.error(f"Scraper failed for query '{q_text}': {e}")

            log.info(f"✅ Scraper completed: {results['scraper']['total_found']} new jobs found.")
            _report("scraper", "Scraping complete", f"✅ Found {results['scraper']['total_found']} new jobs")

            # 3. Matcher Phase (No browser needed)
            log.info("━━ Phase 2: Matcher ━━━━━━━━━━━━━━━━━━━━━━━━")
            _report("matcher", "Matching jobs...", "━━ Phase 2: Matcher")
            try:
                min_match = float(controls.get("min_match", "70"))
                m_res = run_matcher(min_match=min_match)
                results["matcher"] = m_res
                log.info(f"✅ Matcher completed: {m_res.get('scored', 0)} jobs scored.")
                _report("matcher", "Matching complete", f"✅ {m_res.get('scored', 0)} jobs scored")
            except Exception as e:
                log.error(f"❌ Matcher failed: {e}")
                results["matcher"] = {"error": str(e)}
                _report("matcher", "Matcher failed", f"❌ Matcher failed: {e}")

            # 4. Queue Phase (No browser needed)
            log.info("━━ Phase 3: Queue ━━━━━━━━━━━━━━━━━━━━━━━━━━")
            _report("queue", "Ranking jobs...", "━━ Phase 3: Queue")
            try:
                q_res = run_queue()
                results["queue"] = q_res
                log.info(f"✅ Queue ranking completed.")
                _report("queue", "Ranking complete", "✅ Queue ranking completed")
            except Exception as e:
                log.error(f"❌ Queue phase failed: {e}")
                results["queue"] = {"error": str(e)}
                _report("queue", "Queue failed", f"❌ Queue phase failed: {e}")

            # 5. Apply Assistant Phase
            log.info("━━ Phase 4: Apply Assistant ━━━━━━━━━━━━━━━")
            _report("apply", "Processing applications...", "━━ Phase 4: Apply Assistant")
            try:
                # Pass the existing page to the apply assistant
                a_res = run_apply_assistant(headless=headless, page=page)
                results["apply_bot"] = a_res # Keep key for compatibility or rename to assistant
                log.info(f"✅ Apply Assistant completed: {a_res.get('opened', 0)} jobs presented to user.")
                _report("apply", "Applications ready", f"✅ {a_res.get('opened', 0)} jobs ready for review")
            except Exception as e:
                log.error(f"❌ Apply Assistant failed: {e}")
                results["apply_bot"] = {"error": str(e)}
                _report("apply", "Apply assistant failed", f"❌ Apply Assistant failed: {e}")

        except Exception as e:
            log.critical(f"💥 Critical Failure in Agent Cycle: {e}")
            results["error"] = str(e)
            log.error(traceback.format_exc())
            _report("error", "Critical failure", f"💥 Critical Failure: {e}")
        finally:
            browser.close()
            results["finished_at"] = datetime.now(timezone.utc).isoformat()
            results["duration_s"] = int(time.time() - start_time)
            
            # Log results to cycles.jsonl
            try:
                from finder.shared.config import LOGS_DIR
                with open(os.path.join(LOGS_DIR, "cycles.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps(results) + "\n")
            except Exception:
                pass
                
            log.info(f"🏁 Agent Cycle Finished in {results['duration_s']}s.")
            _report("done", "Cycle finished", f"🏁 Finished in {results['duration_s']}s")
        
    return results

def run_agent_loop(interval_hours=6, headless=True):
    """Infinite loop for periodic agent execution."""
    log.info(f"🔄 Agent loop starting (interval: {interval_hours}h, headless={headless})...")
    while True:
        try:
            run_agent_cycle(headless=headless)
        except Exception as e:
            log.error(f"Loop error: {e}")
        
        log.info(f"💤 Sleeping for {interval_hours} hours...")
        time.sleep(interval_hours * 3600)
