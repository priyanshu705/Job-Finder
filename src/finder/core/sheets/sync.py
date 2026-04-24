"""
src/finder/core/sheets/sync.py
-----------------------------
Google Sheets Sync — Finder V6.
"""

import os
import json
from datetime import datetime, timezone, date, timedelta
from typing import Optional

from dotenv import load_dotenv

from finder.shared.logger import get_logger
from finder.shared.database import get_db
from finder.shared.metrics import record_metric

load_dotenv()

log = get_logger("sheets")

# ── Config ────────────────────────────────────────────────────────────────────
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "./credentials.json")
SHEET_ID         = os.getenv("GOOGLE_SHEET_ID", "")
SHEET_TITLE      = os.getenv("GOOGLE_SHEET_TITLE", "Finder V6 — Job Tracker")

# Tab names
TAB_APPLICATIONS = "📋 Applications"
TAB_TOP_MATCHES  = "🎯 Top Matches"
TAB_DAILY_STATS  = "📊 Daily Stats"
TAB_COMPANIES    = "🏢 Companies"
TAB_INSIGHTS     = "🔍 Insights"

ALL_TABS = [TAB_APPLICATIONS, TAB_TOP_MATCHES, TAB_DAILY_STATS, TAB_COMPANIES, TAB_INSIGHTS]


# ── Sheets Client ─────────────────────────────────────────────────────────────

def _get_client():
    """Authenticate with Google Sheets API."""
    if not SHEET_ID:
        raise RuntimeError("GOOGLE_SHEET_ID not set in .env")
    if not os.path.exists(CREDENTIALS_PATH):
        raise RuntimeError(f"Google credentials not found at {CREDENTIALS_PATH}")

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds  = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except ImportError:
        raise RuntimeError("gspread not installed. Run: pip install gspread google-auth")


def _open_sheet(client):
    try:
        return client.open_by_key(SHEET_ID)
    except Exception as exc:
        raise RuntimeError(f"Cannot open sheet {SHEET_ID}: {exc}")


def _get_or_create_tab(sheet, tab_name: str, rows: int = 1000, cols: int = 20):
    try:
        return sheet.worksheet(tab_name)
    except Exception:
        log.info(f"Creating new tab: {tab_name}")
        return sheet.add_worksheet(title=tab_name, rows=rows, cols=cols)


def _write_tab(ws, headers: list, rows: list, freeze_rows: int = 1) -> None:
    all_rows = [headers] + rows
    ws.clear()
    if all_rows:
        ws.update(all_rows, value_input_option="USER_ENTERED")
    try:
        ws.format("1:1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8}})
        ws.format("A1:Z1", {"textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}, "backgroundColor": {"red": 0.15, "green": 0.35, "blue": 0.75}})
        if freeze_rows: ws.freeze(rows=freeze_rows)
    except Exception: pass


def _fmt_ts(ts_raw: str) -> str:
    if not ts_raw: return ""
    try:
        dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception: return str(ts_raw)[:16]


def _status_emoji(status: str) -> str:
    return {"applied": "✅", "uncertain": "⚠️", "failed": "❌", "skip": "⏭️", "pending": "⏳", "external_skip": "🔗", "already_applied": "♻️"}.get(status, "❓")


# ── Tab Syncs ─────────────────────────────────────────────────────────────────

def sync_applications(sheet) -> int:
    log.info("Syncing Applications tab...")
    with get_db() as conn:
        rows = conn.execute("SELECT q.status, q.match_score_at_apply, q.goal_boost, q.risk_score, q.attempts, q.updated_at, q.queued_at, q.last_error, q.is_exploration, j.title, j.company, j.platform, j.location, j.salary, j.skills, j.posted_at, j.job_url, j.form_type FROM apply_queue q LEFT JOIN jobs j ON j.job_url = q.job_url WHERE q.status IN ('applied','uncertain','failed','external_skip','already_applied') ORDER BY q.updated_at DESC LIMIT 500").fetchall()

    headers = ["Status", "Title", "Company", "Location", "Match%", "Goal Boost", "Risk", "Form", "Platform", "Salary", "Skills", "Applied At", "Queued At", "Attempts", "Error", "Explore?", "URL"]
    data_rows = []
    for r in rows:
        r = dict(r)
        score = r.get("match_score_at_apply")
        data_rows.append([f"{_status_emoji(r['status'])} {r['status']}", r.get("title", ""), r.get("company", ""), r.get("location", "") or "", f"{score:.1f}%" if score is not None else "", f"{r.get('goal_boost') or 0:.0f}", f"{r.get('risk_score') or 0:.2f}", r.get("form_type", "") or "", r.get("platform", ""), r.get("salary", "") or "", r.get("skills", "") or "", _fmt_ts(r.get("updated_at", "")), _fmt_ts(r.get("queued_at", "")), r.get("attempts", 0), r.get("last_error", "") or "", "🔍" if r.get("is_exploration") else "", r.get("job_url", "")])

    ws = _get_or_create_tab(sheet, TAB_APPLICATIONS)
    _write_tab(ws, headers, data_rows)
    return len(data_rows)


def sync_top_matches(sheet) -> int:
    log.info("Syncing Top Matches tab...")
    with get_db() as conn:
        rows = conn.execute("SELECT q.status, q.match_score_at_apply, q.goal_boost, q.risk_score, q.is_exploration, j.title, j.company, j.platform, j.location, j.salary, j.skills, j.posted_at, j.job_url, j.form_type FROM apply_queue q LEFT JOIN jobs j ON j.job_url = q.job_url WHERE q.status IN ('pending','skip') AND q.match_score_at_apply IS NOT NULL ORDER BY q.goal_boost DESC NULLS LAST, q.match_score_at_apply DESC LIMIT 100").fetchall()

    headers = ["Status", "Title", "Company", "Location", "Match%", "Goal Boost", "Risk", "Form", "Platform", "Salary", "Skills", "Posted", "Explore?", "URL"]
    data_rows = []
    for r in rows:
        r = dict(r)
        score = r.get("match_score_at_apply")
        data_rows.append([f"{_status_emoji(r['status'])} {r['status']}", r.get("title", ""), r.get("company", ""), r.get("location", "") or "", f"{score:.1f}%" if score is not None else "", f"{r.get('goal_boost') or 0:.0f}", f"{r.get('risk_score') or 0:.2f}", r.get("form_type", "") or "", r.get("platform", ""), r.get("salary", "") or "", r.get("skills", "") or "", r.get("posted_at", "") or "", "🔍" if r.get("is_exploration") else "", r.get("job_url", "")])

    ws = _get_or_create_tab(sheet, TAB_TOP_MATCHES)
    _write_tab(ws, headers, data_rows)
    return len(data_rows)


def sync_daily_stats(sheet) -> int:
    log.info("Syncing Daily Stats tab...")
    with get_db() as conn:
        rows = conn.execute("SELECT date(updated_at) as day, COUNT(*) as total, SUM(CASE WHEN status='applied' THEN 1 ELSE 0 END) as applied, SUM(CASE WHEN status='uncertain' THEN 1 ELSE 0 END) as uncertain, SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed, SUM(CASE WHEN status='skip' THEN 1 ELSE 0 END) as skipped, SUM(CASE WHEN status='external_skip' THEN 1 ELSE 0 END) as external, AVG(CASE WHEN match_score_at_apply IS NOT NULL THEN match_score_at_apply END) as avg_score FROM apply_queue WHERE updated_at IS NOT NULL GROUP BY date(updated_at) ORDER BY day DESC LIMIT 30").fetchall()
        scraped = conn.execute("SELECT date(scraped_at) as day, COUNT(*) as scraped FROM jobs GROUP BY date(scraped_at) ORDER BY day DESC LIMIT 30").fetchall()

    scraped_by_day = {r[0]: r[1] for r in scraped}
    headers = ["Date", "Scraped", "Applied ✅", "Uncertain ⚠️", "Failed ❌", "Skipped ⏭️", "External 🔗", "Avg Match%", "Total Processed"]
    data_rows = []
    for r in rows:
        r = dict(r)
        day, score = r.get("day", ""), r.get("avg_score")
        data_rows.append([day, scraped_by_day.get(day, 0), r.get("applied", 0), r.get("uncertain", 0), r.get("failed", 0), r.get("skipped", 0), r.get("external", 0), f"{score:.1f}%" if score else "", r.get("total", 0)])

    ws = _get_or_create_tab(sheet, TAB_DAILY_STATS)
    _write_tab(ws, headers, data_rows)
    return len(data_rows)


def sync_companies(sheet) -> int:
    log.info("Syncing Companies tab...")
    with get_db() as conn:
        rows = conn.execute("SELECT company, tier, total_applies, total_interviews, interview_rate, response_rate, avg_response_days, last_applied, notes, updated_at FROM company_intelligence ORDER BY interview_rate DESC, total_applies DESC").fetchall()

    headers = ["Company", "Tier", "Total Applied", "Interviews", "Interview Rate", "Response Rate", "Avg Days to Respond", "Last Applied", "Notes", "Updated"]
    tier_emoji = {"tier1": "🌟", "tier2": "⭐", "startup": "🚀", "blacklist": "🚫", "unknown": "❓"}
    data_rows = []
    for r in rows:
        r = dict(r)
        tier = r.get("tier", "unknown")
        ir, rr = r.get("interview_rate") or 0, r.get("response_rate") or 0
        data_rows.append([r.get("company", ""), f"{tier_emoji.get(tier, '')} {tier}", r.get("total_applies", 0), r.get("total_interviews", 0), f"{ir:.0%}", f"{rr:.0%}", f"{r.get('avg_response_days') or 0:.1f}", r.get("last_applied", "") or "", r.get("notes", "") or "", _fmt_ts(r.get("updated_at", ""))])

    ws = _get_or_create_tab(sheet, TAB_COMPANIES)
    _write_tab(ws, headers, data_rows)
    return len(data_rows)


def sync_insights(sheet) -> int:
    log.info("Syncing Insights tab...")
    with get_db() as conn:
        thresh_rows = conn.execute("SELECT date, threshold, success_rate, applied, failed FROM threshold_history ORDER BY date DESC LIMIT 30").fetchall()
        skill_rows = conn.execute("SELECT skill, SUM(CASE WHEN outcome IN ('applied','interview','offer') THEN count ELSE 0 END) as positive, SUM(count) as total FROM skill_outcome_map GROUP BY skill HAVING total >= 1 ORDER BY positive DESC LIMIT 20").fetchall()
        goal_rows = conn.execute("SELECT goal_type, value, priority FROM user_goals WHERE active=1").fetchall()
        ctrl_rows = conn.execute("SELECT key, value, updated_at FROM user_controls").fetchall()

    ws = _get_or_create_tab(sheet, TAB_INSIGHTS)
    ws.clear()
    all_data = []
    all_data.append(["⚙️ SYSTEM CONTROLS", "", ""])
    all_data.append(["Setting", "Value", "Last Updated"])
    for r in ctrl_rows: all_data.append([r[0], r[1], _fmt_ts(r[2])])
    all_data.append(["", "", ""])
    all_data.append(["🎯 ACTIVE GOALS", "", ""])
    all_data.append(["Type", "Value", "Priority"])
    for r in goal_rows: all_data.append([r[0], r[1], r[2]])
    all_data.append(["", "", ""])
    all_data.append(["✅ TOP SKILLS BY OUTCOME", "", ""])
    all_data.append(["Skill", "Positive Outcomes", "Total"])
    for r in skill_rows: all_data.append([r[0], r[1], r[2]])
    all_data.append(["", "", ""])
    all_data.append(["📈 THRESHOLD HISTORY", "", ""])
    all_data.append(["Date", "Threshold", "Success Rate", "Applied", "Failed"])
    for r in thresh_rows: all_data.append([r[0], r[1], f"{r[2] or 0:.1%}", r[3], r[4]])

    ws.update(all_data, value_input_option="USER_ENTERED")
    return len(all_data)


def append_application_row(job: dict, status: str, sheet=None) -> bool:
    """Append a single application row in real-time."""
    try:
        if not SHEET_ID: return False
        client = _get_client()
        sh = sheet or _open_sheet(client)
        ws = _get_or_create_tab(sh, TAB_APPLICATIONS)
        score = job.get("match_score_at_apply")
        row = [f"{_status_emoji(status)} {status}", job.get("title", ""), job.get("company", ""), job.get("location", "") or "", f"{score:.1f}%" if score is not None else "", f"{job.get('goal_boost') or 0:.0f}", f"{job.get('risk_score') or 0:.2f}", job.get("form_type", "") or "", job.get("platform", "internshala"), job.get("salary", "") or "", job.get("skills", "") or "", datetime.now().strftime("%Y-%m-%d %H:%M"), "", "", "", "", job.get("job_url", "")]
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception: return False


def run_sheets_sync(tabs: Optional[list] = None) -> dict:
    """Sync all tabs to Google Sheets."""
    stats = {"synced_tabs": 0, "rows_written": 0, "skipped": False, "error": None}
    if not SHEET_ID or not os.path.exists(CREDENTIALS_PATH):
        stats["skipped"] = True
        return stats
    try:
        client = _get_client()
        sheet = _open_sheet(client)
        sync_tabs = tabs or ALL_TABS
        for tab in sync_tabs:
            try:
                if tab == TAB_APPLICATIONS: n = sync_applications(sheet)
                elif tab == TAB_TOP_MATCHES: n = sync_top_matches(sheet)
                elif tab == TAB_DAILY_STATS: n = sync_daily_stats(sheet)
                elif tab == TAB_COMPANIES: n = sync_companies(sheet)
                elif tab == TAB_INSIGHTS: n = sync_insights(sheet)
                else: continue
                stats["synced_tabs"] += 1
                stats["rows_written"] += n
            except Exception as e: log.error(f"Tab '{tab}' sync failed: {e}")
        record_metric("sheets_sync", "sheets", value=stats["rows_written"])
    except Exception as exc:
        stats["error"] = str(exc)
    return stats
