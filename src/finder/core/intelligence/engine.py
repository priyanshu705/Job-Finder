"""
src/finder/core/intelligence/engine.py
--------------------------------------
Intelligence & Learning Engine — Finder V6.
"""

import os
import json
import re
from datetime import datetime, timezone, date, timedelta
from collections import defaultdict

from dotenv import load_dotenv

from finder.shared.logger import get_logger
from finder.shared.database import get_db
from finder.shared.metrics import record_metric

load_dotenv()

log = get_logger("intelligence")

# ── Config ────────────────────────────────────────────────────────────────────
MIN_SAMPLES_FOR_LEARNING = 3    # need at least this many outcomes to trust signal
THRESHOLD_ADJUST_STEP    = 2.0  # max change per cycle (±2%)
MIN_THRESHOLD            = 40.0
MAX_THRESHOLD            = 85.0
TARGET_SUCCESS_RATE      = 0.30  # aim for 30% of applications getting responses


# ── 1. Company Intelligence ───────────────────────────────────────────────────

def update_company_intelligence() -> dict:
    """Aggregate application_outcomes by company and update company_intelligence."""
    log.info("Updating company intelligence...")

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT company,
                   COUNT(*) as total,
                   SUM(CASE WHEN outcome IN ('applied','uncertain') THEN 1 ELSE 0 END) as applied,
                   SUM(CASE WHEN outcome IN ('interview','offer') THEN 1 ELSE 0 END) as interviews,
                   SUM(CASE WHEN outcome NOT IN ('failed','external_skip','already_applied')
                            THEN 1 ELSE 0 END) as responses,
                   AVG(CASE WHEN days_to_respond IS NOT NULL THEN days_to_respond END) as avg_days
            FROM application_outcomes
            WHERE company IS NOT NULL AND company != ''
            GROUP BY LOWER(company)
            HAVING total >= 1
            """
        ).fetchall()

    stats = {"updated": 0, "new_companies": 0}

    for r in rows:
        r = dict(r)
        company      = r["company"]
        total        = r["total"] or 0
        interviews   = r["interviews"] or 0
        responses    = r["responses"] or 0
        avg_days     = round(r["avg_days"] or 0, 1)

        interview_rate = round(interviews / max(total, 1), 3)
        response_rate  = round(responses  / max(total, 1), 3)

        if interview_rate >= 0.3: tier = "tier1"
        elif interview_rate >= 0.15 or response_rate >= 0.4: tier = "tier2"
        elif total >= 3 and interview_rate == 0: tier = "blacklist"
        else: tier = "startup"

        with get_db() as conn:
            existing = conn.execute(
                "SELECT company FROM company_intelligence WHERE LOWER(company)=LOWER(?)",
                (company,)
            ).fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE company_intelligence SET
                        total_applies     = ?,
                        total_interviews  = ?,
                        interview_rate    = ?,
                        response_rate     = ?,
                        avg_response_days = ?,
                        tier              = ?,
                        updated_at        = CURRENT_TIMESTAMP
                    WHERE LOWER(company) = LOWER(?)
                    """,
                    (total, interviews, interview_rate, response_rate,
                     avg_days, tier, company)
                )
                stats["updated"] += 1
            else:
                conn.execute(
                    """
                    INSERT INTO company_intelligence
                        (company, total_applies, total_interviews,
                         interview_rate, response_rate, avg_response_days, tier)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (company, total, interviews, interview_rate,
                     response_rate, avg_days, tier)
                )
                stats["new_companies"] += 1

    log.info(f"Company intelligence: updated={stats['updated']} new={stats['new_companies']}")
    return stats


# ── 2. Skill Outcome Mapping ──────────────────────────────────────────────────

def update_skill_outcome_map() -> dict:
    """Learn which skills correlate with positive outcomes."""
    log.info("Updating skill outcome map...")

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT ao.outcome, j.skills
            FROM application_outcomes ao
            LEFT JOIN jobs j ON j.job_url = ao.job_url
            WHERE j.skills IS NOT NULL AND j.skills != ''
            """
        ).fetchall()

    skill_counts = defaultdict(lambda: defaultdict(int))
    for r in rows:
        outcome = (r["outcome"] or "unknown").lower()
        skills_raw = r["skills"] or ""
        skills = [s.strip().lower() for s in skills_raw.split(",") if s.strip()]
        for skill in skills[:10]:
            skill_counts[skill][outcome] += 1

    total_mapped = 0
    with get_db() as conn:
        for skill, outcomes in skill_counts.items():
            for outcome, count in outcomes.items():
                conn.execute(
                    """
                    INSERT INTO skill_outcome_map (skill, outcome, count)
                    VALUES (?, ?, ?)
                    ON CONFLICT(skill, outcome) DO UPDATE SET
                        count = count + excluded.count
                    """,
                    (skill, outcome, count)
                )
                total_mapped += 1

    with get_db() as conn:
        top = conn.execute(
            """
            SELECT skill, SUM(count) as total,
                   SUM(CASE WHEN outcome IN ('applied','interview','offer')
                        THEN count ELSE 0 END) as positive
            FROM skill_outcome_map
            GROUP BY skill
            ORDER BY positive DESC
            LIMIT 10
            """
        ).fetchall()

    top_skills = [{"skill": r["skill"], "positive": r["positive"], "total": r["total"]} for r in top]
    log.info(f"Skill map updated: {total_mapped} entries")
    return {"skills_mapped": total_mapped, "top_skills": top_skills}


# ── 3. Threshold Optimisation ─────────────────────────────────────────────────

def optimise_threshold() -> dict:
    """Auto-tune MIN_MATCH based on recent success rates."""
    log.info("Optimising match threshold...")

    with get_db() as conn:
        ctrl = conn.execute("SELECT value FROM user_controls WHERE key='min_match'").fetchone()
        current = float(ctrl["value"] if ctrl else "70")

    since = (date.today() - timedelta(days=30)).isoformat()
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN outcome IN ('interview','offer') THEN 1 ELSE 0 END) as success
            FROM application_outcomes
            WHERE recorded_at >= ?
            """,
            (since,),
        ).fetchone()

    total   = row["total"] or 0
    success = row["success"] or 0
    result = {"old_threshold": current, "new_threshold": current, "success_rate": 0.0, "direction": "unchanged", "samples": total}

    if total < MIN_SAMPLES_FOR_LEARNING:
        return result

    success_rate = success / total
    result["success_rate"] = round(success_rate, 3)

    new_threshold = current
    if success_rate > TARGET_SUCCESS_RATE + 0.10:
        new_threshold = max(current - THRESHOLD_ADJUST_STEP, MIN_THRESHOLD)
        result["direction"] = "lowered"
    elif success_rate < TARGET_SUCCESS_RATE - 0.10:
        new_threshold = min(current + THRESHOLD_ADJUST_STEP, MAX_THRESHOLD)
        result["direction"] = "raised"

    result["new_threshold"] = round(new_threshold, 1)
    if new_threshold != current:
        with get_db() as conn:
            conn.execute("UPDATE user_controls SET value=?, updated_at=CURRENT_TIMESTAMP WHERE key='min_match'", (str(new_threshold),))
            conn.execute("INSERT INTO threshold_history (threshold, success_rate, applied, failed, date) VALUES (?, ?, ?, ?, CURRENT_DATE)", (new_threshold, success_rate, success, total - success))
        log.info(f"Threshold {result['direction']}: {current} → {new_threshold}")

    return result


# ── 4. Failure Pattern Detection ──────────────────────────────────────────────

def update_failure_patterns() -> dict:
    """Detect temporal and platform failure patterns."""
    log.info("Updating failure patterns...")

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT q.last_error, q.updated_at, j.platform
            FROM apply_queue q
            LEFT JOIN jobs j ON j.job_url = q.job_url
            WHERE q.status = 'failed' AND q.last_error IS NOT NULL
            """
        ).fetchall()

    patterns_updated = 0
    for r in rows:
        error_raw = (r["last_error"] or "").lower()
        platform  = (r["platform"] or "internshala").lower()
        ts_raw    = r["updated_at"] or ""

        if "timeout" in error_raw: error_type = "timeout"
        elif "captcha" in error_raw: error_type = "captcha"
        elif "login" in error_raw: error_type = "auth_failure"
        elif "404" in error_raw or "not found" in error_raw: error_type = "page_not_found"
        else: error_type = "generic"

        try:
            dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            hour, dow = dt.hour, dt.weekday()
        except Exception:
            hour, dow = datetime.now().hour, datetime.now().weekday()

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO failure_patterns (module, error_type, platform, hour_of_day, day_of_week, count, last_seen)
                VALUES ('apply_bot', ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(module, error_type, platform, hour_of_day) DO UPDATE SET
                    count = count + 1, last_seen = CURRENT_TIMESTAMP
                """,
                (error_type, platform, hour, dow)
            )
        patterns_updated += 1
    return {"patterns_updated": patterns_updated}


# ── 5. Behavior Signal Logging ────────────────────────────────────────────────

def log_behavior_signal(job_url: str, job_title: str, job_skills: str, action: str, score: float) -> None:
    """Record a single agent decision for later analysis."""
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO behavior_signals (job_url, job_title, job_skills, action, score_at_time) VALUES (?, ?, ?, ?, ?)", (job_url, job_title, job_skills, action, score))
    except Exception: pass


# ── 6. Insight Reporter ────────────────────────────────────────────────────────

def generate_insights() -> dict:
    """Generate human-readable insights from accumulated data."""
    insights = {"best_companies": [], "avoid_companies": [], "best_skills": [], "worst_hours": [], "recommendations": []}

    with get_db() as conn:
        insights["best_companies"] = [dict(r) for r in conn.execute("SELECT company, tier, interview_rate, total_applies FROM company_intelligence WHERE tier IN ('tier1','tier2') AND total_applies >= 1 ORDER BY interview_rate DESC LIMIT 5").fetchall()]
        insights["avoid_companies"] = [dict(r) for r in conn.execute("SELECT company, total_applies, interview_rate FROM company_intelligence WHERE tier = 'blacklist' ORDER BY total_applies DESC LIMIT 5").fetchall()]
        insights["best_skills"] = [dict(r) for r in conn.execute("SELECT skill, SUM(count) as positive, SUM(count) as total FROM skill_outcome_map GROUP BY skill HAVING total >= 2 ORDER BY positive DESC LIMIT 8").fetchall()]
        insights["worst_hours"] = [{"hour": r[0], "failures": r[1]} for r in conn.execute("SELECT hour_of_day, SUM(count) as failures FROM failure_patterns WHERE error_type != 'generic' GROUP BY hour_of_day ORDER BY failures DESC LIMIT 3").fetchall()]

    recs = []
    if insights["avoid_companies"]:
        names = [c["company"] for c in insights["avoid_companies"][:3]]
        recs.append(f"⚠️ Low response from: {', '.join(names)}")
    if insights["best_skills"]:
        skills = [s["skill"] for s in insights["best_skills"][:5]]
        recs.append(f"✅ High-yield skills: {', '.join(skills)}")
    if not recs:
        recs.append("📊 Gathering data...")
    insights["recommendations"] = recs
    return insights


# ── Manual Outcome Recorder ───────────────────────────────────────────────────

def record_outcome(job_url: str, outcome: str, days_to_respond: int = None, notes: str = "") -> None:
    """Manually record an application outcome."""
    with get_db() as conn:
        job = conn.execute("SELECT title, company, platform FROM jobs WHERE job_url=?", (job_url,)).fetchone()
        match_row = conn.execute("SELECT match_score_at_apply FROM apply_queue WHERE job_url=?", (job_url,)).fetchone()

    title, company, platform = (job["title"], job["company"], job["platform"]) if job else ("", "", "")
    score = match_row["match_score_at_apply"] if match_row else None

    with get_db() as conn:
        conn.execute("INSERT INTO application_outcomes (job_url, job_title, company, platform, match_score, outcome, days_to_respond, notes, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (job_url, title, company, platform, score, outcome, days_to_respond, notes, datetime.now(timezone.utc).isoformat()))

    log.info(f"Outcome recorded: [{outcome}] {title}")
    update_company_intelligence()
    update_skill_outcome_map()


# ── Public Entry Point ────────────────────────────────────────────────────────

def run_intelligence() -> dict:
    """Run the full intelligence analysis pipeline."""
    log.info("Running Intelligence Analysis...")
    report = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "company_update": update_company_intelligence(),
        "skill_map": update_skill_outcome_map(),
        "threshold": optimise_threshold(),
        "failure_patterns": update_failure_patterns(),
        "insights": generate_insights(),
    }
    record_metric("intelligence_run", "intelligence", value=1)
    return report
