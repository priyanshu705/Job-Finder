"""
src/finder/api/main.py
----------------------
AutoApply AI — Flask REST API
"""

import os
import json
import logging
import threading
from datetime import datetime, date, timedelta

from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from finder.shared.database import get_db, _USE_POSTGRES
from finder.shared.config import LOGS_DIR
from finder.core.agent import run_agent_cycle

load_dotenv()

log = logging.getLogger(__name__)

app = Flask(__name__)

def _cors_origins():
    origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    )
    return [origin.strip() for origin in origins.split(",") if origin.strip()]

CORS(app, resources={r"/api/*": {"origins": _cors_origins()}}, supports_credentials=True)


_agent_status = {
    "running":     False,
    "phase":       "idle",   # scraper|matcher|queue|apply|done|error
    "progress":    "",
    "logs":        [],
    "last_run":    None,
    "last_result": None,
    "error":       None
}

@app.route("/api/agent/status")
def agent_status():
    return jsonify(_agent_status)

@app.route("/api/agent/run", methods=["POST"])
def run_agent():
    if _agent_status["running"]:
        return jsonify({"error": "Agent already running"}), 400

    def _report_callback(phase, progress, msg=None):
        _agent_status["phase"] = phase
        _agent_status["progress"] = progress
        if msg:
            _agent_status["logs"].append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "msg": msg
            })
            # Keep only last 20 logs
            if len(_agent_status["logs"]) > 20:
                _agent_status["logs"].pop(0)

    log.info("Agent cycle started from UI")
    _agent_status["running"] = True
    _agent_status["last_run"] = datetime.now().isoformat()
    _agent_status["error"] = None
    _agent_status["logs"] = []
    _agent_status["phase"] = "init"
    _agent_status["progress"] = "Initializing..."

    def _run():
        try:
            results = run_agent_cycle(headless=False, report_callback=_report_callback)
            _agent_status["last_result"] = results
            _agent_status["phase"] = "done"
            _agent_status["progress"] = "Cycle completed successfully"
            log.info("Agent cycle completed")
        except Exception as e:
            _agent_status["error"] = str(e)
            _agent_status["phase"] = "error"
            _agent_status["progress"] = f"Error: {e}"
            log.error("Agent cycle failed: %s", e)
        finally:
            _agent_status["running"] = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started"})

CYCLES_LOG = os.path.join(LOGS_DIR, "cycles.jsonl")

def _row_to_dict(r):
    """Convert a sqlite3.Row or psycopg2 RealDictRow to a plain dict."""
    if r is None:
        return {}
    try:
        return dict(r)
    except Exception:
        return {}

def q(sql, params=()):
    with get_db() as conn:
        return [_row_to_dict(r) for r in (conn.execute(sql, params).fetchall() or [])]

def q1(sql, params=()):
    rows = q(sql, params)
    return rows[0] if rows else {}

# ── Status Tracking ───────────────────────────────────────────────────────────

_cycle_state = {
    "phase":      None,   # scraper|matcher|queue|apply|done
    "started_at": None,
    "updated_at": None,
    "last_applied": 0,
    "last_scraped": 0,
}

def update_cycle_state(phase, **kwargs):
    _cycle_state.update({"phase": phase, "updated_at": datetime.now().isoformat(), **kwargs})

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.route("/api/status")
def status():
    try:
        controls   = {r["key"]: r["value"] for r in q("SELECT key,value FROM user_controls")}
        queue_stat = {r["status"]: r["cnt"] for r in
                      q("SELECT status, COUNT(*) as cnt FROM apply_queue GROUP BY status")}
        db_counts  = {
            "jobs":     q1("SELECT COUNT(*) as c FROM jobs").get("c", 0),
            "queue":    q1("SELECT COUNT(*) as c FROM apply_queue").get("c", 0),
            "outcomes": q1("SELECT COUNT(*) as c FROM application_outcomes").get("c", 0),
            "companies":q1("SELECT COUNT(*) as c FROM company_intelligence").get("c", 0),
        }
        today = date.today().isoformat()
        # Use Python-side date comparison — works on both SQLite and PostgreSQL
        _today_start = today + " 00:00:00"
        _today_end   = today + " 23:59:59"
        today_stats = q1(
            """SELECT
                SUM(CASE WHEN status='applied'   THEN 1 ELSE 0 END) as applied,
                SUM(CASE WHEN status='uncertain' THEN 1 ELSE 0 END) as uncertain,
                SUM(CASE WHEN status='failed'    THEN 1 ELSE 0 END) as failed
               FROM apply_queue WHERE updated_at BETWEEN ? AND ?""",
            (_today_start, _today_end),
        )
        manual_req = q1("SELECT value FROM user_controls WHERE key='manual_verification_required'")
        return jsonify({
            "controls":    controls,
            "queue":       queue_stat,
            "db_counts":   db_counts,
            "today":       today_stats,
            "manual_verification_required": manual_req.get("value") if manual_req else None,
            "timestamp":   datetime.now().isoformat(),
        })
    except Exception as e:
        log.error("/api/status error: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/queue")
def queue():
    try:
        status_filter = request.args.get("status", "")
        sort_mode     = request.args.get("sort", "priority")
        limit         = min(int(request.args.get("limit", 50)), 200)  # cap at 200
        offset        = int(request.args.get("offset", 0))
        search_q      = request.args.get("q", "")
        min_score     = request.args.get("min_score", "")
        company       = request.args.get("company", "")

        where_clauses = ["1=1"]
        params = []

        if status_filter:
            where_clauses.append("q.status=?")
            params.append(status_filter)

        if search_q:
            where_clauses.append("(j.title LIKE ? OR j.company LIKE ?)")
            params.extend([f"%{search_q}%", f"%{search_q}%"])

        if min_score:
            try:
                where_clauses.append("q.match_score_at_apply >= ?")
                params.append(float(min_score))
            except ValueError:
                pass

        if company:
            where_clauses.append("j.company LIKE ?")
            params.append(f"%{company}%")

        where = "WHERE " + " AND ".join(where_clauses)

        order = (
            "q.queued_at DESC"
            if sort_mode == "latest"
            else "q.goal_boost DESC NULLS LAST, q.match_score_at_apply DESC NULLS LAST, q.queued_at DESC"
        )

        rows = q(f"""
            SELECT q.id, q.status, q.match_score_at_apply, q.goal_boost,
                   q.risk_score, q.is_exploration, q.attempts,
                   q.queued_at, q.updated_at, q.last_error, q.assistant_data,
                   q.relevance_feedback,
                   j.title, j.company, j.platform, j.location,
                   j.salary, j.skills, j.form_type, j.posted_at, j.job_url
            FROM apply_queue q
            LEFT JOIN jobs j ON j.job_url = q.job_url
            {where}
            ORDER BY {order}
            LIMIT ? OFFSET ?
        """, params + [limit, offset])

        total = q1(f"SELECT COUNT(*) as c FROM apply_queue q LEFT JOIN jobs j ON j.job_url = q.job_url {where}", params).get("c", 0)
        return jsonify({"jobs": rows, "total": total, "limit": limit, "offset": offset})
    except Exception as e:
        log.error("/api/queue error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats/overview")
def stats_overview():
    stats = q1("""
        SELECT 
            SUM(CASE WHEN status='applied_manual' OR status='applied' THEN 1 ELSE 0 END) as applied,
            SUM(CASE WHEN status='interview' THEN 1 ELSE 0 END) as interviews,
            SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) as rejected
        FROM apply_queue
    """)
    
    applied = stats.get("applied") or 0
    interviews = stats.get("interviews") or 0
    # Success Rate: Interview per Application
    success_rate = (interviews / applied * 100) if applied > 0 else 0
    
    return jsonify({
        "cards": [
            {"label": "Total Applied", "value": applied, "icon": "CheckCircle", "color": "emerald"},
            {"label": "Interview Rate", "value": f"{int(success_rate)}%", "icon": "Target", "color": "blue"},
            {"label": "Interviews", "value": interviews, "icon": "Phone", "color": "purple"},
            {"label": "Pending", "value": stats.get("pending") or 0, "icon": "Clock", "color": "amber"}
        ]
    })

@app.route("/api/jobs/<int:job_id>/feedback", methods=["POST"])
def update_feedback(job_id):
    fb = (request.json or {}).get("feedback")
    with get_db() as conn:
        conn.execute("UPDATE apply_queue SET relevance_feedback=? WHERE id=?", (fb, job_id))
    return jsonify({"success": True})

@app.route("/api/demo/seed", methods=["POST"])
def seed_demo_data():
    """Seed realistic demo data — idempotent, safe to call multiple times."""
    try:
        # (title, company, platform, location, skills, salary, url, status, score, ai_json)
        DEMO_JOBS = [
            ("Senior QA Automation Engineer", "Razorpay",   "Internshala", "Remote",    "Python, Selenium, Playwright, CI/CD",   "12-18 LPA", "https://demo.com/1", "applied",   92.0, '{"summary":"Strong match. Applied automatically.","why":"Skills align 92%."}'),
            ("Python Backend Developer",      "Groww",      "LinkedIn",    "Bangalore", "FastAPI, PostgreSQL, Redis, Docker",     "10-15 LPA", "https://demo.com/2", "interview", 88.0, '{"summary":"Excellent fit. Interview scheduled.","why":"Backend exp matches perfectly."}'),
            ("Automation Test Engineer",      "PhonePe",    "Internshala", "Hyderabad", "Selenium, TestNG, Java, JIRA",          "8-12 LPA",  "https://demo.com/3", "applied",   85.0, '{"summary":"Good match. Applied.","why":"Testing skills match 85%."}'),
            ("Junior Software Tester",        "Infosys",    "Internshala", "Pune",      "Manual Testing, Selenium, Agile",       "4-6 LPA",   "https://demo.com/4", "pending",   78.0, '{"summary":"Solid entry-level fit.","why":"Testing background fits."}'),
            ("SDET Engineer",                 "Flipkart",   "LinkedIn",    "Bangalore", "Python, Robot Framework, API Testing",  "14-20 LPA", "https://demo.com/5", "pending",   81.0, '{"summary":"Strong technical match.","why":"Python + API testing = great fit."}'),
            ("Test Automation Lead",          "Zomato",     "Naukri",      "Remote",    "Playwright, Cypress, TypeScript",       "18-25 LPA", "https://demo.com/6", "pending",   74.0, '{"summary":"Partial match.","why":"Automation skills relevant."}'),
            ("Backend Engineer - Python",     "Cred",       "LinkedIn",    "Bangalore", "Python, Django, REST APIs, AWS",        "12-16 LPA", "https://demo.com/7", "failed",    69.0, '{"summary":"Below threshold.","why":"AWS skills gap."}'),
            ("QA Engineer - Mobile",          "Meesho",     "Internshala", "Remote",    "Appium, Android Testing, Python",       "7-10 LPA",  "https://demo.com/8", "applied",   83.0, '{"summary":"Good mobile testing match.","why":"Python + Appium = strong fit."}'),
        ]

        _job_upsert = (
            "INSERT INTO jobs (title, company, platform, location, skills, salary, job_url) "
            "VALUES (?,?,?,?,?,?,?) ON CONFLICT (job_url) DO NOTHING"
            if _USE_POSTGRES else
            "INSERT OR IGNORE INTO jobs (title, company, platform, location, skills, salary, job_url) VALUES (?,?,?,?,?,?,?)"
        )
        _q_upsert = (
            "INSERT INTO apply_queue (job_url, status, match_score_at_apply, goal_boost, attempts, assistant_data, updated_at) "
            "VALUES (?,?,?,1.1,1,?,CURRENT_TIMESTAMP) ON CONFLICT (job_url) DO NOTHING"
            if _USE_POSTGRES else
            "INSERT OR IGNORE INTO apply_queue (job_url, status, match_score_at_apply, goal_boost, attempts, assistant_data, updated_at) "
            "VALUES (?,?,?,1.1,1,?,CURRENT_TIMESTAMP)"
        )
        _ci_upsert = (
            "INSERT INTO company_intelligence (company, tier, total_applies, interview_rate, response_rate) "
            "VALUES (?,?,?,?,?) ON CONFLICT (company) DO NOTHING"
            if _USE_POSTGRES else
            "INSERT OR IGNORE INTO company_intelligence (company, tier, total_applies, interview_rate, response_rate) "
            "VALUES (?,?,?,?,?)"
        )

        with get_db() as conn:
            for title, company, platform, loc, skills, salary, url, status, score, ai in DEMO_JOBS:
                conn.execute(_job_upsert, (title, company, platform, loc, skills, salary, url))
                conn.execute(_q_upsert, (url, status, score, ai))
            for company, tier, applies, irate, rrate in [
                ("Razorpay", "A", 4, 0.50, 0.75), ("Groww",    "A", 3, 0.67, 0.80),
                ("PhonePe",  "A", 2, 0.50, 0.60), ("Flipkart", "B", 5, 0.40, 0.55),
                ("Zomato",   "B", 3, 0.33, 0.45), ("Infosys",  "B", 6, 0.17, 0.40),
                ("Meesho",   "B", 2, 0.50, 0.65), ("Cred",     "A", 1, 0.00, 0.30),
            ]:
                conn.execute(_ci_upsert, (company, tier, applies, irate, rrate))

        return jsonify({"seeded": True, "jobs": len(DEMO_JOBS)})
    except Exception as e:
        log.error("/api/demo/seed error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/jobs")
def jobs():
    limit  = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    search = request.args.get("q", "")

    if search:
        rows = q("""
            SELECT id,title,company,platform,location,salary,skills,
                   form_type,posted_at,job_url,scraped_at
            FROM jobs
            WHERE title LIKE ? OR company LIKE ? OR skills LIKE ?
            ORDER BY scraped_at DESC LIMIT ? OFFSET ?
        """, (f"%{search}%",)*3 + (limit, offset))
        total = q1("""SELECT COUNT(*) as c FROM jobs
                     WHERE title LIKE ? OR company LIKE ? OR skills LIKE ?""",
                   (f"%{search}%",)*3)["c"]
    else:
        rows  = q("SELECT * FROM jobs ORDER BY scraped_at DESC LIMIT ? OFFSET ?",
                  (limit, offset))
        total = q1("SELECT COUNT(*) as c FROM jobs")["c"]

    return jsonify({"jobs": rows, "total": total})

@app.route("/api/stats/daily")
def stats_daily():
    try:
        days  = int(request.args.get("days", 30))
        since = (date.today() - timedelta(days=days)).isoformat()

        # CAST to DATE works on both SQLite and PostgreSQL
        daily = q("""
            SELECT CAST(updated_at AS DATE) as date,
                   SUM(CASE WHEN status='applied' OR status='applied_manual' THEN 1 ELSE 0 END) as applied,
                   SUM(CASE WHEN status='failed'    THEN 1 ELSE 0 END) as failed,
                   SUM(CASE WHEN status='uncertain' THEN 1 ELSE 0 END) as uncertain,
                   SUM(CASE WHEN status='interview' THEN 1 ELSE 0 END) as interviews
            FROM apply_queue
            WHERE updated_at >= ? AND updated_at IS NOT NULL
            GROUP BY CAST(updated_at AS DATE)
            ORDER BY CAST(updated_at AS DATE) ASC
        """, (since,))

        scraped = q("""
            SELECT CAST(scraped_at AS DATE) as day, COUNT(*) as scraped
            FROM jobs WHERE scraped_at >= ?
            GROUP BY CAST(scraped_at AS DATE)
        """, (since,))
        scraped_map = {str(r["day"]): r["scraped"] for r in scraped}

        for row in daily:
            row["date"] = str(row["date"])  # ensure string for JSON
            row["scraped"] = scraped_map.get(row["date"], 0)

        return jsonify(daily)
    except Exception as e:
        log.error("/api/stats/daily error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats/summary")
def stats_summary():
    try:
        since = (date.today() - timedelta(days=7)).isoformat()
        row   = q1("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status='applied' OR status='applied_manual' THEN 1 ELSE 0 END) as applied,
                   SUM(CASE WHEN status='failed'    THEN 1 ELSE 0 END) as failed,
                   SUM(CASE WHEN status='uncertain' THEN 1 ELSE 0 END) as uncertain,
                   SUM(CASE WHEN status='skip' OR status='skipped' THEN 1 ELSE 0 END) as skipped,
                   AVG(match_score_at_apply) as avg_score
            FROM apply_queue
            WHERE updated_at >= ?
        """, (since,))
        alltime = q1("""
            SELECT COUNT(*) as total_jobs,
                   SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending,
                   SUM(CASE WHEN status='interview' THEN 1 ELSE 0 END) as interviews
            FROM apply_queue
        """)
        total_applied = (row.get("applied") or 0) + (row.get("uncertain") or 0)
        return jsonify({
            **row,
            "total_applied": total_applied,
            "period_days":   7,
            "pending":       alltime.get("pending") or 0,
            "interviews":    alltime.get("interviews") or 0,
            "total_jobs":    alltime.get("total_jobs") or 0,
        })
    except Exception as e:
        log.error("/api/stats/summary error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/goals", methods=["GET"])
def get_goals():
    return jsonify(q("SELECT * FROM user_goals WHERE active=1 ORDER BY priority DESC"))

@app.route("/api/goals", methods=["POST"])
def add_goal():
    data  = request.json or {}
    gtype = data.get("goal_type", "keyword")
    value = data.get("value", "")
    prio  = int(data.get("priority", 5))
    if not value:
        return jsonify({"error": "value required"}), 400
    try:
        if _USE_POSTGRES:
            # RETURNING id is required — psycopg2 doesn't populate lastrowid
            rows = q(
                "INSERT INTO user_goals (goal_type,value,priority,active) VALUES(?,?,?,1) RETURNING id",
                (gtype, value, prio)
            )
            gid = rows[0]["id"] if rows else None
        else:
            with get_db() as conn:
                cur = conn.execute(
                    "INSERT INTO user_goals (goal_type,value,priority,active) VALUES(?,?,?,1)",
                    (gtype, value, prio)
                )
                gid = cur.lastrowid
        return jsonify({"id": gid, "goal_type": gtype, "value": value, "priority": prio}), 201
    except Exception as e:
        log.error("/api/goals POST error: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/goals/<int:gid>", methods=["DELETE"])
def delete_goal(gid):
    with get_db() as conn:
        conn.execute("UPDATE user_goals SET active=0 WHERE id=?", (gid,))
    return jsonify({"deleted": gid})

@app.route("/api/companies")
def companies():
    rows = q("""
        SELECT company, tier, total_applies, total_interviews,
               interview_rate, response_rate, avg_response_days,
               last_applied, updated_at
        FROM company_intelligence
        ORDER BY interview_rate DESC, total_applies DESC
        LIMIT 100
    """)
    return jsonify(rows)

@app.route("/api/insights")
def insights():
    try:
        best_skills = q("""
            SELECT skill,
                   SUM(CASE WHEN outcome IN ('applied','interview','offer')
                       THEN count ELSE 0 END) as positive,
                   SUM(count) as total
            FROM skill_outcome_map GROUP BY skill
            HAVING total>=1 ORDER BY positive DESC LIMIT 10
        """)
        threshold_hist = q("""
            SELECT date, threshold, success_rate, applied, failed
            FROM threshold_history ORDER BY date DESC LIMIT 10
        """)
        failure_pat = q("""
            SELECT module, error_type, platform, hour_of_day, SUM(count) as count
            FROM failure_patterns GROUP BY module, error_type, platform, hour_of_day
            ORDER BY count DESC LIMIT 10
        """)
        outcomes = q("""
            SELECT outcome, COUNT(*) as cnt FROM application_outcomes
            GROUP BY outcome ORDER BY cnt DESC
        """)
        return jsonify({
            "best_skills":      best_skills,
            "threshold_history":threshold_hist,
            "failure_patterns": failure_pat,
            "outcomes":         outcomes,
        })
    except Exception as e:
        log.error("/api/insights error: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/controls", methods=["GET"])
def get_controls():
    return jsonify({r["key"]: r["value"] for r in
                    q("SELECT key,value FROM user_controls")})

@app.route("/api/controls", methods=["POST"])
def update_control():
    data = request.json or {}
    key  = data.get("key")
    val  = data.get("value")
    if not key:
        return jsonify({"error": "key required"}), 400
    with get_db() as conn:
        conn.execute(
            "UPDATE user_controls SET value=?,updated_at=CURRENT_TIMESTAMP WHERE key=?",
            (str(val), key)
        )
    return jsonify({"key": key, "value": val})

# ── Actions ───────────────────────────────────────────────────────────────────

_running = {}

def _run_async(name, fn):
    if _running.get(name):
        return {"status": "already_running", "task": name}
    def _task():
        _running[name] = True
        try:
            fn()
        finally:
            _running[name] = False
    t = threading.Thread(target=_task, daemon=True)
    t.start()
    return {"status": "started", "task": name}

@app.route("/api/actions/pause", methods=["POST"])
def pause():
    with get_db() as conn:
        conn.execute("UPDATE user_controls SET value='true' WHERE key='paused'")
    return jsonify({"paused": True})

@app.route("/api/actions/resume", methods=["POST"])
def resume():
    with get_db() as conn:
        conn.execute("UPDATE user_controls SET value='false' WHERE key='paused'")
        conn.execute("DELETE FROM user_controls WHERE key='manual_verification_required'")
    return jsonify({"paused": False, "manual_verification_cleared": True})

@app.route("/api/actions/reset", methods=["POST"])
def reset_queue():
    with get_db() as conn:
        conn.execute("UPDATE apply_queue SET status='pending',match_score_at_apply=NULL")
    return jsonify({"reset": True})

@app.route("/api/jobs/<int:job_id>/status", methods=["POST"])
def update_job_status(job_id):
    data = request.json or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "status required"}), 400
    with get_db() as conn:
        conn.execute(
            "UPDATE apply_queue SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (new_status, job_id)
        )
    return jsonify({"id": job_id, "status": new_status})

@app.route("/api/actions/scrape", methods=["POST"])
def trigger_scrape():
    from finder.core.scraper import run_scraper
    return jsonify(_run_async("scraper", run_scraper))

@app.route("/api/actions/scrape-visible", methods=["POST"])
def trigger_scrape_visible():
    from finder.core.scraper import run_scraper
    return jsonify(_run_async("scraper", lambda: run_scraper(headless=False)))

@app.route("/api/actions/match", methods=["POST"])
def trigger_match():
    from finder.core.matcher import run_matcher
    return jsonify(_run_async("matcher", run_matcher))

@app.route("/api/actions/rank", methods=["POST"])
def trigger_rank():
    from finder.core.queue import run_queue
    return jsonify(_run_async("queue", run_queue))

@app.route("/api/actions/cycle", methods=["POST"])
def trigger_cycle():
    from finder.core.agent import run_agent_cycle
    data   = request.json or {}
    kwargs = {
        "duration_minutes":    int(data.get("duration_minutes", 5)),
        "max_apply_per_cycle": int(data.get("max_apply", 5)),
        "headless":            data.get("headless", True),
    }
    return jsonify(_run_async("agent", lambda: run_agent_cycle(**kwargs)))

@app.route("/api/actions/status")
def action_status():
    return jsonify({k: v for k, v in _running.items()})

@app.route("/api/outcomes", methods=["POST"])
def record_outcome():
    data = request.json or {}
    url  = data.get("job_url")
    out  = data.get("outcome")
    if not url or not out:
        return jsonify({"error": "job_url and outcome required"}), 400
    from finder.core.intelligence import record_outcome as _rec
    _rec(url, out, data.get("days_to_respond"), data.get("notes", ""))
    return jsonify({"recorded": True}), 201

@app.route("/api/activity")
def activity():
    limit  = int(request.args.get("limit", 20))
    events = []

    if os.path.exists(CYCLES_LOG):
        try:
            with open(CYCLES_LOG, "r", encoding="utf-8") as f:
                lines = f.readlines()[-50:]
            for line in reversed(lines):
                try:
                    cyc = json.loads(line.strip())
                    ts  = cyc.get("started_at", cyc.get("finished_at", ""))
                    s   = cyc.get("scraper",   {})
                    m   = cyc.get("matcher",   {})
                    ab  = cyc.get("apply_bot", {})
                    dur = cyc.get("duration_s", 0)

                    if ab.get("applied", 0):
                        events.append({"ts": ts, "type": "apply",
                            "msg": f"Applied to {ab['applied']} jobs",
                            "icon": "✅", "level": "success"})
                    if s.get("new_jobs", 0):
                        events.append({"ts": ts, "type": "scrape",
                            "msg": f"Found {s['new_jobs']} new jobs (scraped {s.get('scraped',0)})",
                            "icon": "🕷️", "level": "info"})
                    if m.get("passed", 0):
                        events.append({"ts": ts, "type": "match",
                            "msg": f"Scored {m.get('scored',0)} jobs · {m['passed']} passed threshold",
                            "icon": "🎯", "level": "info"})
                    if cyc.get("error"):
                        events.append({"ts": ts, "type": "error",
                            "msg": f"Cycle error: {cyc['error']}",
                            "icon": "❌", "level": "error"})
                    events.append({"ts": ts, "type": "cycle",
                        "msg": f"Cycle completed in {dur}s",
                        "icon": "🔄", "level": "muted"})
                except Exception: pass
        except Exception: pass

    if _running.get("agent") and _cycle_state.get("phase"):
        events.insert(0, {
            "ts":    _cycle_state.get("updated_at", ""),
            "type":  "running",
            "msg":   f"Cycle running · phase: {_cycle_state['phase']}",
            "icon":  "⚡",
            "level": "running",
        })

    try:
        # Use Python-computed threshold — works on both SQLite and PostgreSQL
        _since = (datetime.utcnow() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        recent = q("""
            SELECT q.status, q.updated_at, j.title, j.company
            FROM apply_queue q
            LEFT JOIN jobs j ON j.job_url = q.job_url
            WHERE q.status IN ('applied','uncertain','failed')
              AND q.updated_at >= ?
            ORDER BY q.updated_at DESC LIMIT 10
        """, (_since,))
        for r in recent:
            icon  = "✅" if r["status"] == "applied" else "⚠️" if r["status"] == "uncertain" else "❌"
            level = "success" if r["status"] == "applied" else "warn" if r["status"] == "uncertain" else "error"
            events.insert(0, {
                "ts":    str(r["updated_at"]) if r["updated_at"] else "",
                "type":  r["status"],
                "msg":   f"{icon} {r['status'].title()}: {r['title'] or '?'} @ {r['company'] or '?'}",
                "icon":  icon,
                "level": level,
            })
    except Exception: pass

    events.sort(key=lambda e: e.get("ts", ""), reverse=True)
    return jsonify(events[:limit])

@app.route("/api/cycle-status")
def cycle_status():
    return jsonify({
        "running":     _running.get("agent", False),
        "phase":       _cycle_state.get("phase"),
        "started_at":  _cycle_state.get("started_at"),
        "updated_at":  _cycle_state.get("updated_at"),
        "last_applied":_cycle_state.get("last_applied", 0),
        "last_scraped":_cycle_state.get("last_scraped", 0),
        "tasks":       dict(_running),
    })

@app.route("/api/health")
def health():
    db_status = "disconnected"
    try:
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
        db_status = "connected"
    except Exception as e:
        log.warning("Health DB probe failed: %s", e)
    return jsonify({
        "status": "ok" if db_status == "connected" else "degraded",
        "name": "AutoApply AI",
        "version": "3.0",
        "db": db_status,
        "ts": datetime.now().isoformat(),
    })

# ── Global error handlers — always return JSON, never HTML tracebacks ─────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "method not allowed"}), 405

@app.errorhandler(500)
def internal_error(e):
    log.error("Unhandled 500: %s", e)
    return jsonify({"error": "internal server error"}), 500

@app.errorhandler(Exception)
def unhandled_exception(e):
    log.error("Unhandled exception: %s", e, exc_info=True)
    return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "5000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug, use_reloader=debug)
